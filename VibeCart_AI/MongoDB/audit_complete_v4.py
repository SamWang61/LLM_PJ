"""Read-only audit of the latest complete schema, fields and migration evidence."""
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
from xml.etree import ElementTree as ET
from bson import json_util
from bootstrap_schema import ROOT,connect
from schema_complete_v4 import CORE,PRESERVED,SCHEMAS,verify_complete


def field_rows(schema,prefix=''):
    required=set(schema.get('required',[]))
    for name,definition in schema.get('properties',{}).items():
        path=prefix+name
        kind=definition.get('bsonType','enum')
        if isinstance(kind,list):kind='/'.join(kind)
        constraints={k:v for k,v in definition.items() if k not in ('bsonType','properties','items','required')}
        encoded=json_util.dumps(constraints,ensure_ascii=False).replace('|','&#124;') if constraints else '—'
        yield f'|{path}|{kind}|{"是" if name in required else "否"}|{encoded}|\n'
        nested=definition.get('items',definition)
        if 'properties' in nested:
            yield from field_rows(nested,path+('[]' if 'items' in definition else '')+'.')
        additional=definition.get('additionalProperties')
        if isinstance(additional,dict) and 'properties' in additional:
            yield from field_rows(additional,path+'.<key>.')


def main():
    with connect() as c:
        db=c.vibecart_ai
        report=verify_complete(db)
        migrations=list(db.schema_migrations.find({}))
        extras=sorted(set(db.list_collection_names())-set(SCHEMAS))
        payload={'checked_at':datetime.now(timezone.utc),'database':'vibecart_ai','core_collections':CORE,
            'preserved_collections':PRESERVED,'extra_collections':extras,'migrations':migrations,'collections':report,
            'system_configs':list(db.system_configs.find({}))}
    snapshot=json_util.dumps(payload,ensure_ascii=False,indent=2)
    (ROOT/'05_實際Schema與索引.md').write_text('# Atlas 最新完整 Schema 讀回\n\n新版核心 19 集合 v4，另保留 8 集合。\n\n```json\n'+snapshot+'\n```\n',encoding='utf-8')
    suite=next(ET.parse(ROOT/'complete_v4_test_results.xml').getroot().iter('testsuite'))
    if int(suite.attrib['failures']) or int(suite.attrib['errors']):raise RuntimeError('Latest test suite failed')
    total=sum(len(r['indexes']) for r in report)
    unique=sum(bool(i.get('unique')) for r in report for i in r['indexes'] if i['name']!='_id_')
    ttl=[r['collection'] for r in report for i in r['indexes'] if 'expireAfterSeconds' in i]
    text='# 完整 Schema v4 實際驗證與逐欄位字典\n\n'
    text+='查核時間：'+datetime.now(timezone.utc).isoformat()+'\n\n'
    text+=f'**{len(report)} 集合、{len(report)} strict/error validators、{total-len(report)} 自訂索引、{total} 總索引；自訂唯一索引 {unique} 個。**\n\n'
    text+='TTL 僅：'+', '.join(ttl)+'。新事件、評價、首推快照及統計集合不自動刪除。\n\n'
    text+=f'新版測試：{suite.attrib["tests"]} passed，耗時 {suite.attrib["time"]} 秒；[JUnit XML](complete_v4_test_results.xml)。此結果是 Complete Schema v4 測試，不是之前的同數量 v2/v3 測試。\n\n'
    text+='## 資料與遷移紀錄\n\n|集合|定位|文件數|合規數|自訂索引|\n|---|---|---|---|---|\n'
    for r in report:
        text+=f'|{r["collection"]}|{"新版核心 v4" if r["collection"] in CORE else "保留既有"}|{r["count"]}|{r["conforming_documents"]}|{len(r["indexes"])-1}|\n'
    text+='\n建立前 6 個重設計集合均為空；沒有猜測舊 SKU、分類、評價或訂單關聯。只新增 1 筆文件明列的推薦政策設定，不生成假評價、歷史交易、推薦結果或統計。測試資料按測試專用 ObjectId 清除，最终數量如上表。\n\n'
    text+='|Migration|狀態|Checksum|\n|---|---|---|\n'
    for m in migrations:text+=f'|{m["_id"]}|{m["status"]}|{m["checksum"]}|\n'
    text+='\n## 本次驗證涵蓋\n\n'
    text+='- 全部 27 集合的有效文件可寫入，缺少 schema_version 被拒，寫入測試均回滾。\n'
    text+='- 偏好分數 70／30 上限、評價 1～5 整數、SKU Decimal128、available_quantity 一致性。\n'
    text+='- 預設4.0與實際評價分離；13/3 顯示4.4，錯誤4.3被拒。\n'
    text+='- 推薦6／4筆上限與首次推薦4.5門檻的文件驗證。\n'
    text+='- 同商品多SKU可同車、結帳重新驗價、重送不重扣、獨立order_items與每商品一筆PURCHASE。\n'
    text+='- 任一SKU失敗整筆回滾、兩位會員搶最後一件僅一單成功。\n'
    text+='- 未送達／未完成訂單不可評價，同會員同明細只能一次；第一筆有效評價不計預設4.0。\n\n'
    text+='## 來源與界線\n\n'
    source=ROOT/'13_完整Schema_v1.0_來源快照.md'
    text+='依據 [完整規格來源](13_完整Schema_v1.0_來源快照.md)，SHA-256：`'+sha256(source.read_bytes()).hexdigest()+'`。\n\n'
    text+='資料庫模型已更新；完整推薦候選產生、跨集合首推資格與marker交易、分數衰減批次、補貨統計批次、關聯規則探勘及排程尚未部署。Schema 約束只能驗證文件形狀與本文件內的計算，不能代替跨集合資格檢查、模型執行或排程。Flask原網站尚未接上新服務。\n\n'
    text+='Atlas外掛本次仍要求OAuth重新登入；實際寫入與讀回使用先前授權的PyMongo帳號，沒有變更Cluster方案。\n\n'
    text+='## 逐欄位定義\n\n'
    for name in CORE+PRESERVED:
        text+=f'### {name}\n\n|欄位|BSON型別|必填|限制|\n|---|---|---|---|\n'
        text+=''.join(field_rows(SCHEMAS[name]['$jsonSchema']))+'\n'
    (ROOT/'16_完整Schema_v4驗證與欄位字典.md').write_text(text,encoding='utf-8')
    print(f'Audit: {len(report)} collections, {total-len(report)} custom indexes, {unique} unique, {suite.attrib["tests"]} tests')


if __name__=='__main__':main()
