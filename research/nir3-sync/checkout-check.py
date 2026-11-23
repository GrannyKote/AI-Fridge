"""Exercise the existing checkout and read handlers via in-process ASGI on a fresh SQLite file."""
from datetime import datetime
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory


def run(folder):
    dbpath = Path(folder, 'fixture.sqlite').resolve()
    os.environ.update(DATABASE_URL='sqlite:///' + dbpath.as_posix(), POSTGRES_HOST='',
                      DB_SCHEMA='main')
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.database import Base, SessionLocal, engine
    from app.models import StoragePlace, UnitOfMeasurement, Product, ProductCategory
    from app.models import UserGroupPurchase, UserGroupPurchaseProduct
    from app.routers import pantry, shopping

    assert engine.dialect.name == 'sqlite' and Path(engine.url.database).resolve() == dbpath
    Base.metadata.create_all(engine)
    app = FastAPI()
    app.include_router(pantry.router)
    app.include_router(shopping.router)
    with SessionLocal() as s:
        s.add_all([StoragePlace(id=1, name='Холодильник'), UnitOfMeasurement(id=1, name='шт'),
                   ProductCategory(id=1, name='Молочные'),
                   Product(id=1, name='Молоко', id_product_category=1)])
        for group in range(1, 5):
            s.add(UserGroupPurchase(id=group, id_user_group=group, create_date_time=datetime.now()))
            s.add(UserGroupPurchaseProduct(id=group, id_user_group=group, id_product=1,
                  product_name='Молоко', id_unit_of_measurement=1, quantity=1,
                  id_product_category=1, id_user_group_purchase=group, create_date_time=datetime.now()))
        s.commit()
    try:
        with TestClient(app) as client:
            orders = [('CPL', (1, 0)), ('PCL', (0, 0)), ('LCP', (1, 1)), ('PLC', (0, 1))]
            for group, (order, expected) in enumerate(orders, 1):
                base = f'/api/groups/{group}'
                seen = {}
                for op in order:
                    if op == 'C':
                        res = client.post(base+'/purchase/checkout', json={'items': [
                            {'id': group, 'quantity': 1, 'storage_place_id': 1, 'best_before': '2026-12-14'}]})
                        assert res.status_code == 204, res.text
                    else:
                        resource = 'products' if op == 'P' else 'purchases'
                        res = client.get(base + '/' + resource)
                        res.raise_for_status()
                        seen[op] = len(res.json())
                assert (seen['P'], seen['L']) == expected
                assert len(client.get(base+'/products').json()) == 1
                assert client.get(base+'/purchases').json() == []
                print(json.dumps({'order': order, 'pantry': seen['P'], 'shopping': seen['L']}))
    finally:
        engine.dispose()


if __name__ == '__main__':
    with TemporaryDirectory() as folder:
        run(folder)
