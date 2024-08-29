import asyncio
from pyppeteer import launch
from bs4 import BeautifulSoup
import requests
import time

async def get_asn_data_ipip(url):
    browser = await launch(headless=True)
    page = await browser.newPage()
    await page.goto(url)
    await page.waitForSelector('table.tablesorter tbody tr')

    content = await page.content()
    await browser.close()

    soup = BeautifulSoup(content, 'html.parser')
    asn_data_ipip = {}
    table_rows = soup.select('table.tablesorter tbody tr')
    print(f"Found {len(table_rows)} rows in the table.")  # Debug output

    for row in table_rows:
        asn_number = row.select_one('td:nth-of-type(1)').text.replace('AS', '')
        asn_name = row.select_one('td:nth-of-type(2)').text.strip()
        asn_data_ipip[asn_number] = asn_name

    return asn_data_ipip

def get_asn_data_he(url, headers):
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return {}

    soup = BeautifulSoup(response.text, 'html.parser')
    asn_data_he = {}

    table_rows = soup.select('#asns tbody tr')
    for row in table_rows:
        asn_number = row.select_one('td:nth-of-type(1) a').text.replace('AS', '')
        asn_name = row.select_one('td:nth-of-type(2)').text.strip()
        asn_data_he[asn_number] = asn_name

    return asn_data_he

def merge_asn_data(asn_data_he, asn_data_ipip):
    merged_data = {}
    print("Merging ASN data...")  # Debug output

    # 首先添加来自 asn_data_he 的数据
    for asn_number, asn_name in asn_data_he.items():
        merged_data[asn_number] = asn_name
        print(f"Added {asn_number} from he.net: {asn_name}")  # Debug output
    
    # 然后处理来自 asn_data_ipip 的数据
    for asn_number, asn_name in asn_data_ipip.items():
        if asn_number in merged_data:
            # 如果 ASN 已存在，比较名称长度
            existing_name = merged_data[asn_number]
            if existing_name == '' or len(asn_name) > len(existing_name):
                merged_data[asn_number] = asn_name  # 更新为更详细的名称
                print(f"Updated {asn_number} with ipip name: {asn_name}")  # Debug output
            else:
                print(f"Skipped updating {asn_number}, existing name is more detailed: {existing_name}")  # Debug output
        else:
            # 如果 ASN 不在 merged_data 中，直接添加
            merged_data[asn_number] = asn_name
            print(f"Added {asn_number} from ipip: {asn_name}")  # Debug output

    return merged_data


def write_asn_file(filename, asn_data):
    local_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    total_asn = len(asn_data)
    with open(filename, 'w', encoding='utf-8') as asn_file:
        asn_file.write("// ASN CN from: https://bgp.he.net/country/CN and https://whois.ipip.net/iso/CN\n")
        asn_file.write(f"// Last Updated: UTC {local_time}\n")
        asn_file.write(f"// Total ASN: {total_asn}\n")
        asn_file.write("// Made by budaobu.\n\n")

        for asn_number, asn_name in asn_data.items():
            if asn_name:
                asn_file.write(f"IP-ASN,{asn_number} // {asn_name}\n")
            else:
                asn_file.write(f"IP-ASN,{asn_number}\n")

def main():
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15"
    }

    # Get data from bgp.he.net
    url_he = "https://bgp.he.net/country/CN"
    asn_data_he = get_asn_data_he(url_he, headers)
    print(f"Total ASNs from he.net: {len(asn_data_he)}")  # Debug output

    # Get data from whois.ipip.net
    url_ipip = "https://whois.ipip.net/iso/CN"
    asn_data_ipip = asyncio.run(get_asn_data_ipip(url_ipip))
    print(f"Total ASNs from ipip.net: {len(asn_data_ipip)}")  # Debug output

    # Merge data
    merged_asn_data = merge_asn_data(asn_data_he, asn_data_ipip)
    print(f"Total merged ASNs: {len(merged_asn_data)}")  # Debug output

    # 安全检查：确保没有丢失任何 ASN
    assert len(merged_asn_data) >= len(asn_data_he), "Some ASNs from he.net were lost during merging"
    assert len(merged_asn_data) >= len(asn_data_ipip), "Some ASNs from ipip.net were lost during merging"

    # Write to file
    output_filename = "asn_cn.list"
    write_asn_file(output_filename, merged_asn_data)

if __name__ == "__main__":
    main()
