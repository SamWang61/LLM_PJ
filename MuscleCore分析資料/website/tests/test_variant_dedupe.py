"""6+4 shows a product once even when the catalog lists a single pack and a [箱購] case."""
from datetime import datetime, timezone
import pytest
from bson import ObjectId
from app.services.storefront_ranking import is_pack_variant, recommendations_6_4, variant_key
from test_storefront_6_4 import product

BOX_NOTE = "(箱購依實際收貨為主，無法保證原封箱出貨)"


@pytest.mark.parametrize("single,box", [
    ("牛頭牌金鑽玉米粒340g", "[箱購]牛頭牌金鑽玉米粒340g x 24Can罐" + BOX_NOTE),
    ("一度贊-爌肉(碗) 200g", "一度贊-爌肉(碗) 200g" + BOX_NOTE),
    ("波爾天然水1500ml", "波爾天然水1500ml" + BOX_NOTE),
    ("Sunny Ranch 蜜汁腰果350g", "[箱購]Sunny Ranch 蜜汁腰果350g克 x 12Bucket桶/箱" + BOX_NOTE),
    ("沙拉脫800ml", "[箱購]沙拉脫800ml毫升x12瓶/箱" + BOX_NOTE),
    ("飲用水1.5L", "[箱購]飲用水1.5L x 6瓶"),
])
def test_single_and_box_share_a_key(single, box):
    assert variant_key(single) == variant_key(box)
    assert is_pack_variant(box) and not is_pack_variant(single)


@pytest.mark.parametrize("a,b", [
    ("[箱購]UNIDESIGN純水 1500ml" + BOX_NOTE, "[箱購]UNIDESIGN純水 6000ml"),             # different volume
    ("[箱購]Sunny Ranch 蜜汁腰果350g克 x 12Bucket桶", "[箱購]Sunny Ranch 綜合纖果350g克x12Bucket桶"),  # different flavour
    ("光泉果汁時刻蘋果汁TP-250ml", "光泉果汁時刻芭芒柳汁TP250ml"),
    ("[箱購]飲用水1.5L x 6瓶", "[箱購]飲用水15L x 1桶"),
    ("[箱購]食材0.5kg x 6袋", "[箱購]食材05kg x 1袋"),
])
def test_different_products_keep_different_keys(a, b):
    assert variant_key(a) != variant_key(b)


def test_personal_block_shows_one_pack_and_fills_the_slot():
    major, minor = ObjectId(), ObjectId()
    single = product(major, minor, 4.9, name="波爾天然水1500ml")
    box = product(major, minor, 5.0, name="波爾天然水1500ml" + BOX_NOTE)
    other = product(major, minor, 4.6, name="泰山純水700ml")
    result = recommendations_6_4([single, box, other], [])
    names = [item["product"]["name"] for item in result["personalized"]]
    assert names == [box["name"], other["name"]]  # higher-rated pack wins; the single pack is not repeated


def test_cross_block_skips_a_variant_already_shown():
    viewed_major, other_major = ObjectId(), ObjectId()
    shown = product(viewed_major, ObjectId(), 4.9, name="牛頭牌金鑽玉米粒340g")
    case = product(other_major, ObjectId(), 5.0, name="[箱購]牛頭牌金鑽玉米粒340g x 24Can罐" + BOX_NOTE)
    events = [{"event_type": "PRODUCT_VIEW", "product_id": shown["_id"], "event_at": datetime.now(timezone.utc)}]
    result = recommendations_6_4([shown, case], events)
    assert [i["product"]["name"] for i in result["personalized"]] == [shown["name"]]
    assert result["cross_category"] == []


def test_identical_plain_names_are_not_merged():
    major, minor = ObjectId(), ObjectId()
    products = [product(major, minor, name="test") for _ in range(3)]
    assert len(recommendations_6_4(products, [])["personalized"]) == 3


def test_distinct_decimal_capacities_both_remain_recommended():
    major, minor = ObjectId(), ObjectId()
    products = [product(major, minor, 4.9, name="[箱購]飲用水1.5L x 6瓶"),
                product(major, minor, 4.8, name="[箱購]飲用水15L x 1桶")]
    assert len(recommendations_6_4(products, [])["personalized"]) == 2
