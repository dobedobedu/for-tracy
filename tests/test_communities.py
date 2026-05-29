from engine.parser import extract_community


def test_extract_community_from_address():
    assert extract_community("8504 ANTHIRIUM Loop, Sarasota, FL 34240") == "ANTHIRIUM"
    assert extract_community("8582 SEA MIST Loop, Sarasota, FL 34240") == "SEA MIST"
    assert extract_community("126 NERUDA Ln, Sarasota, FL 34240") == "NERUDA"
    assert extract_community("123 MAIN St, Sarasota, FL 34240") == "MAIN"
    assert extract_community("9255 AUGER Ln, Sarasota, FL 34240") == "AUGER"
    assert extract_community("2628 WATERFRONT Cir, Sarasota, FL 34240") == "WATERFRONT"
    assert extract_community("240 BLUE MIST Way, Sarasota, FL 34240") == "BLUE MIST"
    assert extract_community("1031 BLUE SHELL Loop, Sarasota, FL 34240") == "BLUE SHELL"
    assert extract_community("2320 SHADOW OAKS Rd, Sarasota, FL 34240") == "SHADOW OAKS"


def test_extract_community_with_suffix():
    assert extract_community("1262 PALM VIEW Rd, Sarasota, FL 34240") == "PALM VIEW"


def test_extract_community_no_commas():
    assert extract_community("8504 ANTHIRIUM Loop Sarasota FL 34240") == "ANTHIRIUM"
