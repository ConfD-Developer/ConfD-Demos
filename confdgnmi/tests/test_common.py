import pytest

from confd_gnmi_common import make_name_keys, make_gnmi_path, make_xpath_path, \
    make_formatted_path


@pytest.mark.parametrize("input, output", [
    ("name[key1=val1]", ("name", {"key1": "val1"})),
    ("name[key1=val1][key2=val2]",
     ("name", {"key1": "val1", "key2": "val2"})),
    ("name[key1=val1][key2=val2][key3=val3]",
     ("name", {"key1": "val1", "key2": "val2", "key3": "val3"})),
])
def test_make_name_keys(input, output):
    (name, keys) = make_name_keys(input)
    assert name == output[0]
    assert keys == output[1]


@pytest.mark.parametrize("path",
                         ["/name1", "/", "/name1/name2", "/name1[key1=val1]"])
def test_make_path(path):
    def xpath_to_formatted(xpath):
        formatted = ""
        for elem in path.split('/'):
            formatted += "/"
            if elem != "":
                elem_string = elem
                if "[" in elem:
                    namekeys = make_name_keys(elem)
                    elem_string = namekeys[0]
                    for k, v in namekeys[1].items():
                        elem_string +="{{{}}}".format(v)
                formatted += elem_string
        formatted = formatted.replace("//", "/")
        return formatted

    gnmi_path = make_gnmi_path(path)
    xpath_path = make_xpath_path(gnmi_path)
    assert path == xpath_path
    formatted_path = make_formatted_path(gnmi_path)
    assert xpath_to_formatted(path) == formatted_path
