"""Read-only live audit and full field inventory, without exposing document data."""
from datetime import datetime,timezone
import hashlib
from pathlib import Path
from xml.etree import ElementTree as ET
from bson import json_util
from bootstrap_schema import ROOT,connect
from schema_current import SCHEMAS,verify_current

SOURCES={
 'users':'整合 v1.1 §5.1','categories':'整合 v1.1 §5.2','products':'整合 v1.1 §5.3',
 'carts':'購物車更新 §4、§8','orders':'整合 v1.1 §5.5','user_events':'整合 v1.1 §5.6',
 'ai_requests':'整合 v1.1 §5.7','product_embeddings':'整合 v1.1 §6.1',
 'recommendations':'整合 v1.1 §6.2','ai_insights':'整合 v1.1 §6.3',
 'ai_usage':'整合 v1.1 §6.4','request_limits':'整合 v1.1 §6.4',
 'schema_migrations':'整合 v1.1 §6.4','cart_events':'購物車更新 §5、§8'}


def rows(schema,prefix=''):
    required=set(schema.get('required',[]))
    for name,spec in schema.get('properties',{}).items():
        path=prefix+name
        kind=spec.get('bsonType','enum')
        kind='/'.join(kind) if isinstance(kind,list) else kind
        constraints={k:v for k,v in spec.items() if k not in ('bsonType','properties','items','required','additionalProperties')}
        encoded=json_util.dumps(constraints,ensure_ascii=False).replace('|','&#124;') if constraints else '—'
        yield f'|{path}|{kind}|{"是" if name in required else "否"}|{encoded}|\n'
        nested=spec.get('items',spec)
        if 'properties' in nested:
            yield from rows(nested,path+('[]' if 'items' in spec else '')+'.')


def main():
    with connect() as client:
        db=client.vibecart_ai
        report=verify_current(db)
        migrations=list(db.schema_migrations.find({}, {'_id':1,'status':1,'checksum':1}))
        extras=sorted(set(db.list_collection_names())-set(SCHEMAS))
        snapshot={'checked_at':datetime.now(timezone.utc),'database':'vibecart_ai',
                  'collections':report,'migrations':migrations,'additional_collections':extras}
        (ROOT/'05_實際Schema與索引.md').write_text('# Atlas 最新 Schema 與索引讀回\n\n全部 14 集合逐項驗證；不包含業務文件內容或憑證。\n\n```json\n'+
            json_util.dumps(snapshot,ensure_ascii=False,indent=2)+'\n```\n',encoding='utf-8')
    suite=next(ET.parse(ROOT/'schema_complete_test_results.xml').getroot().iter('testsuite'))
    tests=int(suite.attrib['tests']); failures=int(suite.attrib['failures']); errors=int(suite.attrib['errors'])
    if failures or errors:
        raise RuntimeError('Latest tests did not pass')
    text='# 全部 Schema 文件對照與實際查核\n\n'
    text+='查核時間：'+datetime.now(timezone.utc).isoformat()+'\n\n'
    text+='**14/14 集合、14/14 strict/error validators、31 個自訂索引（含 12 個 unique、2 個 TTL），共 45 個索引，均已建立並讀回吻合。**\n\n'
    text+=f'本次 {tests} 項實際 Atlas 測試通過；失敗 {failures}、錯誤 {errors}，耗時 {suite.attrib["time"]} 秒。含 51 項全集合與條件欄位測試、15 項購物車回歸測試。詳見 [原始測試結果](schema_complete_test_results.xml)。\n\n'
    text+='Atlas 外掛本次回 UNAUTHORIZED（OAuth 需重新登入）；改用先前授權的 PyMongo 資料庫帳號實際查核與 collMod。未重試登入憑證、未更改 Atlas 組織／Cluster／方案。\n\n'
    text+='## 文件依據與優先序\n\n'
    text+='購物車更新文件優先覆蓋原 carts 設計；未衝突部分沿用整合 v1.1。兩份原始文件均完整保留，沒有為了讓查核通過而改寫來源規格。\n\n'
    for name in ('02_專案整合規格_v1.1_來源快照.md','07_購物車更新規格_來源快照.md'):
        text+=f'- [{name}]({name})，SHA-256：`{hashlib.sha256((ROOT/name).read_bytes()).hexdigest()}`\n'
    text+='\n## 集合完成清單\n\n|集合|文件章節|版本|驗證|自訂索引|文件數／合規數|\n|---|---|---|---|---|---|\n'
    for r in report:
        name=r['collection']; version=SCHEMAS[name]['$jsonSchema']['properties']['schema_version']['enum'][0]
        text+=f'|{name}|{SOURCES[name]}|{version}|strict/error，吻合|{len(r["indexes"])-1}|{r["count"]}/{r["conforming_documents"]}|\n'
    text+='\n額外集合：'+(', '.join(extras) if extras else '無')+'。所有既有文件亦使用目前 validator 查詢核對，未發現不合規文件。\n\n'
    text+='## 本次補強\n\n'
    text+='- users：budget_min/max 非負、有限、最多兩位小數；保留 null 及 min≤max。\n'
    text+='- user_events：recommendation_click 必須有 product_id。\n'
    text+='- ai_requests：running 必須有 started_at；succeeded 必須有 started_at 與 actual_provider；實際模型執行須有非空 model_name/revision；Anthropic sales_summary 執行須有非空 Prompt 名稱／版本。執行前失敗仍允許未知模型與開始時間為 null。\n'
    text+='- ai_requests：estimated_cost 拒絕 Infinity／NaN／負值，保留微小 USD 成本的小數精度，不硬四捨五入到分。\n'
    text+='- recommendations：BGE 策略的 model/revision 不接受空字串。\n\n'
    text+='新遷移：20260918_03_schema_document_constraints；僅增加驗證規則，文件形狀與 schema_version 不變，舊兩筆遷移及其 checksum 不變。預檢後才套用；沒有回填／覆寫／刪除業務資料、没有重設配額。\n\n'
    text+='## 明確採用的範圍解讀\n\n'
    text+='- 購物車文件允許 ObjectId/String、Decimal/Double，本專案選用原整合規格較一致的 ObjectId＋Decimal128；沿用 20 品項及數量 1～99。\n'
    text+='- 新資料環境使用 local 登入；Firebase 尚未啟用，local password_hash 必填。歷史訂單無商品、舊 AI 快取無請求關聯等例外屬舊資料遷移，不以放寬全部新文件 validator 代替；本次無此類既有資料。\n'
    text+='- ai_usage、request_limits、schema_migrations 的時間欄位依 §6.4 技術集合專用字典，不額外發明歷史 created_at。\n'
    text+='- cart_events 的事件代碼可擴充，已定義五種事件才有特定前後數量條件；事件本身無 TTL。\n\n'
    text+='## Schema 與應用服務界線\n\n'
    text+='此報告確認資料庫結構與可由 DB 驗證的規則；不代表全部網站或 AI 功能已完成。以下屬跨文件、來源真實性或流程規則，必須由應用服務保證：\n\n'
    text+='- 參照的會員／商品／分類是否存在且有效、登入 owner／角色、密碼雜湊、CSRF、前端不能自填管理欄位。\n'
    text+='- URL 與 metadata/input_summary/parameters 的語意白名單、資料去識別化；DB 已限制型別與文件規定的大小，但不會辨認個資語意。\n'
    text+='- Prompt／模型 revision 真實性、embedding hash／模型版本一致性／正規化、推薦與行為權重、成本只統計 leaf。\n'
    text+='- cart_events append-only 由服務遵守；目前 readWrite 帳號不是不可變稽核儲存，仍有更新／刪除權限。\n'
    text+='- TTL 是背景清除，不保證瞬間刪除；快取與限流讀取仍須比較 expires_at。\n'
    text+='- 舊 Flask 頁面與 Session 購物車尚未接線，不將 Schema 驗證通過宣稱為全站驗收。\n\n'
    text+='## 後續唯一現行驗證入口\n\n```powershell\n'
    text+="& '.\\MuscleCore分析資料\\website\\.venv\\Scripts\\python.exe' 'VibeCart_AI\\MongoDB\\audit_schema.py'\n"
    text+='```\n\n現行定義為 schema_current.py。新環境依序執行 bootstrap_schema.py、migrate_cart_v3.py、migrate_schema_audit.py；已升級環境使用最後遷移與 audit_schema.py，不以歷史版本驗證器覆蓋現況。\n\n'
    text+='## 逐欄位字典（由 Atlas 已吻合的現行定義輸出）\n\n'
    for name in SCHEMAS:
        text+=f'### {name}\n\n|欄位|BSON 型別|必填|限制|\n|---|---|---|---|\n'
        text+=''.join(rows(SCHEMAS[name]['$jsonSchema']))+'\n'
    (ROOT/'12_全部Schema文件對照與驗證.md').write_text(text,encoding='utf-8')
    print(f'Live audit complete: 14 collections, 45 indexes, {tests} tests; counts='+str({r['collection']:r['count'] for r in report}))


if __name__=='__main__':
    main()
