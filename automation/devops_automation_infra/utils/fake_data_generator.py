from devops_automation_infra.snippets import generate_fake_data
from devops_automation_infra.plugins.memsql import Memsql

def fake_poi(host, number=10000):
    memsql_password = host.Memsql.password
    host.SSH.run_snippet(generate_fake_data.fake_poi, number, memsql_password, excludes=['numpy', 'core_product'])
