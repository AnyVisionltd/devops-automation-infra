import pytest

from pytest_automation_infra.helpers import hardware_config
from devops_plugins import postgresql

def init_and_upsert_query(postgres_plugin):
    query1 = f'''INSERT INTO cameras (id, title,pipe,description,"videoUrl",status,"cameraGroupId")
                VALUES('99999999-daac-9999-bf22-4db9e2e7b1e4', 'test1_pasha',' ','test1_description','http://username:password@210.12.23.32/camera', 'DISCONNECTED','00000000-0200-4c1b-4e12-1ba74bff4a4b')'''
    query2 = f'''INSERT INTO cameras (id, title,pipe,description,"videoUrl",status,"cameraGroupId")
                VALUES('99999999-daac-8888-bf22-4db9e2e7b1e4', 'test2_pasha',' ','test2_description','http://username:password@210.12.23.32/camera', 'DISCONNECTED','00000000-0200-4c1b-4e12-1ba74bff4a4b')'''
    postgres_plugin.upsert(query1)
    postgres_plugin.upsert(query2)
    response = postgres_plugin.fetch_count(
        "select count(id) as count from cameras where id = '99999999-daac-9999-bf22-4db9e2e7b1e4' or id = '99999999-daac-8888-bf22-4db9e2e7b1e4'")
    assert response == 2


def fetch_all(postgres_plugin):
    response = postgres_plugin.fetch_all("SELECT * FROM cameras where title = 'test1_pasha' or title = 'test2_pasha'")
    assert len(response) == 2


def fetch_one(postgres_plugin):
    response = postgres_plugin.fetch_one("SELECT * FROM cameras where id = '99999999-daac-9999-bf22-4db9e2e7b1e4'")
    assert response[1] == 'test1_pasha'


def fetch_count(postgres_plugin):
    response = postgres_plugin.fetch_count(
        "select count(id) as count from cameras where title = 'test1_pasha' or title = 'test2_pasha'")
    assert response == 2


def delete_cameras_by_ids(postgres_plugin):
    postgres_plugin.upsert(
        "delete from cameras where id = '99999999-daac-9999-bf22-4db9e2e7b1e4' or id = '99999999-daac-8888-bf22-4db9e2e7b1e4' ")
    response = postgres_plugin.fetch_count(
        "select count(id) as count from cameras where title = 'test1_pasha' or title = 'test2_pasha'")
    assert response == 0


def test_postgresql(base_config):
    postgres_plugin = base_config.host.Postgresql
    delete_cameras_by_ids(postgres_plugin)
    init_and_upsert_query(postgres_plugin)
    fetch_all(postgres_plugin)
    fetch_one(postgres_plugin)
    fetch_count(postgres_plugin)
    delete_cameras_by_ids(postgres_plugin)
