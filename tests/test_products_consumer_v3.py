# This file is part of the Consumer API example.
#
# Copyright (C) 2023 Serghei Iakovlev <egrep@protonmail.ch>
#
# For the full copyright and license information, please view
# the LICENSE file that was distributed with this source code.

"""Pact test for Product service client."""

import atexit
import json
import logging

import pytest
from pact import PactV3, Provider
from pact.matchers_v3 import EachLike
from consumer import exceptions
from consumer.client import Client
from consumer.models import Product
from .factories_v3 import (
    Format,
    HeadersFactory,
    NotFoundErrorFactory,
    ProductFactory,
)
# from .factories import (
#     Format,
#     HeadersFactory,
#     NotFoundErrorFactory,
#     ProductFactory,
# )

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


@pytest.fixture(scope='session')
def mock_service(mock_opts, pact_dir, app_version):
    """Set up a Pact Consumer, which provides the Provider mock service."""
    mock_service = PactV3('ProductServiceClientV3', 
                      'ProductServiceV3', 
                    #   version=app_version,
                      pact_dir=pact_dir,
                        # **mock_opts
                        )
    return mock_service



def test_get_existent_product(mock_service: PactV3, client: Client):
    # Define the Matcher; the expected structure and content of the response
    expected = ProductFactory(name='product0')
    # headers = HeadersFactory.create()  # type: dict
    # headers.update({'Last-Modified': Format().last_modified})

    # Define the expected behaviour of the Provider. This determines how the
    # Pact mock provider will behave. In this case, we expect a body which is
    # "Like" the structure defined above. This means the mock provider will
    # return the EXACT content where defined, e.g. 'product0' for name, and
    # SOME appropriate content e.g. for description.
    (mock_service
     .new_http_interaction('a PactV3 example')
     .given('there is a product with ID 1')
     .upon_receiving('a request for a product')
     .with_request('get', '/v2/products/1')
     .will_respond_with(200, body=expected, headers=[{'name': 'Last-Modified', 'value': Format().last_modified.}]))

    with mock_service:
        mock_service.start_service()
        # Perform the actual request
        product = client.products.get(1)

        # In this case the mock Provider will have returned a valid response
        assert product.name == expected['name']

        # Make sure that all interactions defined occurred
        mock_service.verify()


def test_get_nonexistent_product(mock_service: PactV3, client: Client):
    (mock_service
     .new_http_interaction('a PactV3 example')
     .given('there is no product with ID 7777')
     .upon_receiving('a request for a product')
     .with_request('get', '/v2/products/7777')
     .will_respond_with(404, body=NotFoundErrorFactory(), headers={
        'Content-Type': Format().media_type_json,
     }))

    with mock_service:
        mock_service.start_service()
        with pytest.raises(exceptions.NotFoundError):
            # Perform the actual request
            _ = client.products.get(7777)

        # Make sure that all interactions defined occurred
        mock_service.verify()


def test_delete_nonexistent_product_no_if_match(mock_service: PactV3, client: Client):
    expected = {
        'code': 428,
        'status': 'Precondition Required',
    }

    (mock_service
     .new_http_interaction('a PactV3 example')
     .given('there is no product with ID 7777')
     .upon_receiving('a request to delete a product')
     .with_request('delete', '/v2/products/7777')
     .will_respond_with(428, body=expected, headers={
        'Content-Type': Format().media_type_json,
     }))

    with mock_service:
        mock_service.start_service()
        with pytest.raises(exceptions.PreconditionRequired):
            # Perform the actual request
            _ = client.products.delete(7777)

        # Make sure that all interactions defined occurred
        mock_service.verify()


def test_empty_products_response(mock_service: PactV3, client: Client):
    headers = HeadersFactory.create()  # type: dict
    headers.update({'X-Pagination': '{"total": 0, "total_pages": 0}'})

    (mock_service
     .new_http_interaction('a PactV3 example')
     .given('there are no products')
     .upon_receiving('a request to get list of products')
     .with_request('get', '/v2/products')
     .will_respond_with(200, body=[], headers=headers))

    with mock_service:
        mock_service.start_service()
        # Perform the actual request
        rv = client.products.all()

        # In this case the mock Provider will have returned a valid response
        assert isinstance(rv, list)
        assert len(rv) == 0

        # Make sure that all interactions defined occurred
        mock_service.verify()


def test_products_response(mock_service: PactV3, client: Client):
    expected = EachLike(ProductFactory(), minimum=3)
    headers = HeadersFactory.create()  # type: dict
    headers.update({'X-Pagination': json.dumps({
        'total': 3,
        'total_pages': 1,
        'first_page': 1,
        'last_page': 1,
        'page': 1,
    })})

    (mock_service
     .new_http_interaction('a PactV3 example')
     .given('there are few products')
     .upon_receiving('a request to get list of products')
     .with_request('get', '/v2/products')
     .will_respond_with(200, body=expected, headers=headers))

    with mock_service:
        mock_service.start_service()
        # Perform the actual request
        rv = client.products.all()

        # In this case the mock Provider will have returned a valid response
        assert isinstance(rv, list)
        assert len(rv) >= 3
        assert isinstance(rv[0], Product)
        assert isinstance(rv[1], Product)
        assert isinstance(rv[2], Product)

        # Make sure that all interactions defined occurred
        mock_service.verify()


def test_no_products_in_category_response(mock_service: PactV3, client: Client):
    headers = HeadersFactory.create()  # type: dict
    headers.update({'X-Pagination': '{"total": 0, "total_pages": 0}'})

    (mock_service
     .new_http_interaction('a PactV3 example')
     .given('there are no products in category #2')
     .upon_receiving('a request to get list of products')
     .with_request('get', '/v2/products', query={'cid': '2'})
     .will_respond_with(200, body=[], headers=headers))

    with mock_service:
        mock_service.start_service()
        # Perform the actual request
        rv = client.products.all(query={'cid': 2})

        # In this case the mock Provider will have returned a valid response
        assert isinstance(rv, list)
        assert len(rv) == 0

        # Make sure that all interactions defined occurred
        mock_service.verify()


def test_products_in_category_response(mock_service: PactV3, client: Client):
    expected = EachLike(ProductFactory(category_id=2), minimum=2)
    headers = HeadersFactory.create()  # type: dict
    headers.update({'X-Pagination': json.dumps({
        'total': 2,
        'total_pages': 1,
        'first_page': 1,
        'last_page': 1,
        'page': 1,
    })})

    (mock_service
     .new_http_interaction('a PactV3 example')
     .given('there are few products in category #2')
     .upon_receiving('a request to get list of products')
     .with_request('get', '/v2/products', query={'cid': '2'})
     .will_respond_with(200, body=expected, headers=headers))

    with mock_service:
        mock_service.start_service()
        # Perform the actual request
        rv = client.products.all(query={'cid': 2})

        # In this case the mock Provider will have returned a valid response
        assert isinstance(rv, list)
        assert len(rv) == 2
        assert isinstance(rv[0], Product)
        assert isinstance(rv[1], Product)
        assert rv[0].category_id == 2
        assert rv[1].category_id == 2

        # Make sure that all interactions defined occurred
        mock_service.verify()


def test_create_product(mock_service: PactV3, client: Client):
    headers = HeadersFactory.create()  # type: dict
    location = Format().url(
        '/v2/products/1',
        'https://example.com/v2/products/1'
    )
    headers.update({'Location': location})

    payload = {
        'description': 'test',
        'discount': 241.93,
        'price': 442.95,
        'rating': 5.0,
        'stock': 123,
        'name': 'test',
        'category_id': 1,
        'brand_id': 1,
    }

    expected = ProductFactory(**payload)

    (mock_service
     .new_http_interaction('a PactV3 example')
     .given('there is category #1 and brand #1')
     .upon_receiving('a request to create product')
     .with_request('post', '/v2/products', body=payload, headers={
        'Content-Type': Format().media_type_json
     })
     .will_respond_with(201, body=expected, headers=headers))

    with mock_service:
        mock_service.start_service()
        # Perform the actual request
        rv = client.products.create(**payload)

        # In this case the mock Provider will have returned a valid response
        assert isinstance(rv, Product)
        assert rv.price == 442.95

        # Make sure that all interactions defined occurred
        mock_service.verify()
