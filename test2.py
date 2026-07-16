import json
from pathlib import Path
import requests

url = "https://www.lazada.co.id/catalog/"

querystring = {
    "ajax": "true",
    "isFirstRequest": "true",
    "page": "1",
    "q": "iphone"
}

headers = {
    "Host": "www.lazada.co.id",
    "Connection": "keep-alive",
    "sec-ch-ua-platform": "\"macOS\"",
    "X-CSRF-TOKEN": "e13f363474905",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "sec-ch-ua": "\"Chromium\";v=\"146\", \"Not-A.Brand\";v=\"24\", \"Google Chrome\";v=\"146\"",
    "sec-ch-ua-mobile": "?0",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Referer": "https://www.lazada.co.id/",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.9",
    "Cookie": "__wpkreporterwid_=5cfcb52d-c4b4-4795-119f-30e42e746814; t_fv=1775464601947; t_uid=hT88Ke7LhEFcJaOPLtuBhlyOCEv5Fj1S; lzd_cid=733cfa48-53a6-4642-b2be-2c50d3d98207; lzd_sid=106968ca7d881a288378262c58691948; _tb_token_=e13f363474905; userLanguageML=id; lwrid=AgGdYe%2FkoSlm%2Fs508CfXxe5uI7qt; cna=n15aIp8Z1loCAV25opOUweRB; xlly_s=1; hng=ID|id-ID|IDR|360; hng.sig=to18pG508Hzz7EPB_okhuQu8kDUP3TDmLlnu4IbIOY8; EGG_SESS=S_Gs1wHo9OvRHCMp98md7G31zsLHem5qxSpsESQ91O5A_2QCXwP3pEFs90xRFJmm-klaM0uBRfMl5Y8ZNT5-mezvjoOYB2Ggx4j8Dlcg6H_rGKBBoPaSEypRjXvnMJ1jkO7VoVN6WRDpZSQSkcSsAS7FhUIrWZe4zvxmdtriKEI=; undefined_click_time=1775464713927; t_sid=cKNb0WJ3EYuaD41lpoKMbyjOMy4pXTwh; utm_channel=NA; _m_h5_tk=abae9c682217a900ad0aa14a5ea72399_1775557454445; _m_h5_tk_enc=43378800ec9974fafc100da63b97fe99; lwrtk=AAIEadUopcCqJPZl1c9IuUfekPtGIPjiGjIecmsosOPXNrov/a4iJTE=; tfstk=fOV-92mzjZLJhO5JQJ60tpLdpN7Dw7UyDuz6tDmkdoEY5P-odkXPdXEavvNoZy1KJma1zucSxkCQRywut8XzDUPYXBAl4TzB9XcCjGfGsrBrTXsgVBiSo3unJLgBx4ibKZDV7GfGsz6SzX4fj8mN1kMsRXgSVDtfk20KAQZIFsGj02uBV2O5krTIwQ96UKR4_-351WfllDAXt2H-frC2Xh6IohmLPqOBVmsSFcGKDBOQD4aB7b1XN1nbEJNoG7sfpjaanugx66LKkRUjN4EF_Ql75rwIeWBH7DyYlRDY3Ubrk7UT9VHfMngtBSNoa-I9scw4RWHbzGpZoJagZJIz95VTAG-iX2v5kZpeLYg46K2AUdG8j00xja1JLpkI7qnGk6peLY_Ekcb-gpJE3A1..; epssw=12*CvMv2ItGGIAwfACnM7oIYMrO8FUFsmbbVJdcDJ31RwYwrjoP4UTzlGGGMLczlMohBfILSxCTlGGG6z46oCLDqunwmyOuMKxEl7OzrwGUaTE9mdU02wu24i3f5-BezMTxlfWboNVnjRQUNrEbayXVFW4vAUYkbu7wONGKRGIoXf7tS1hz8iClzRGofHHx9R0XJTrRRx3gO-Kdy-wdXy_m50wGD3Egd0IpbtGGGtbOWWRTvGQGskqh8xhOtrfN1_OoGECxGGGnJn7r1n4CRF7HSNUgrwRGR5vkjtUXe3wq-wgURmcKRGzlmQM973UILlpfYushBX9iG5TFYshU2F3XcCwxQibw92f2o8GSnROShr8K"
}

response = requests.get(url, headers=headers, params=querystring)

print(response.text)

data = response.json()
out_path = Path(__file__).resolve().parent / "lazada_search_items.json"
out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Saved JSON -> {out_path}")