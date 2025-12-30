"""
Tests for CSV expense parsing endpoint.
"""
import pytest
import io
from models import db, Category, Budget
from base64 import b64encode


@pytest.fixture
def setup_test_data(app):
    """Set up test categories and budgets."""
    with app.app_context():
        # Create categories
        personal_cat = Category(name='Dining', parent_type='Personal')
        shared_cat = Category(name='Groceries', parent_type='Shared')
        db.session.add_all([personal_cat, shared_cat])
        db.session.commit()

        # Create budgets
        personal_budget = Budget(category_id=personal_cat.id, user='user1', monthly_amount=500)
        shared_budget = Budget(category_id=shared_cat.id, user=None, monthly_amount=1000)
        db.session.add_all([personal_budget, shared_budget])
        db.session.commit()

        yield {
            'personal_cat': personal_cat,
            'shared_cat': shared_cat
        }


def get_auth_header(username='user1', password='password123'):
    """Helper to create Basic Auth header."""
    credentials = b64encode(f'{username}:{password}'.encode()).decode('utf-8')
    return {'Authorization': f'Basic {credentials}'}


def test_parse_csv_format1_yyyy_mm_dd(client, setup_test_data):
    """Test parsing CSV with YYYY-MM-DD date format."""
    csv_content = '''"2025-12-01","SEND E-TFR ***sG3","36",,"7774.9"
"2025-12-01","PTS FRM: 05966297412",,"1000","8774.9"
"2025-12-01","ENBRIDGE GAS A4A6W8","79.75",,"8695.15"
"2025-12-01","ENOVA WTRLOO A4A6W9","102.46",,"8592.69"'''

    data = {
        'file': (io.BytesIO(csv_content.encode()), 'test.csv')
    }

    response = client.post(
        '/api/expenses/parse-csv',
        data=data,
        headers=get_auth_header(),
        content_type='multipart/form-data'
    )

    assert response.status_code == 200
    data = response.json

    # Should parse 3 expenses (skip the money_in transaction)
    assert data['total_parsed'] == 3
    assert len(data['expenses']) == 3

    # Check first expense
    assert data['expenses'][0]['date'] == '2025-12-01'
    assert data['expenses'][0]['description'] == 'SEND E-TFR ***sG3'
    assert data['expenses'][0]['amount'] == 36.0

    # Check third expense
    assert data['expenses'][2]['amount'] == 102.46


def test_parse_csv_format2_mm_dd_yyyy(client, setup_test_data):
    """Test parsing CSV with MM/DD/YYYY date format."""
    csv_content = '''12/28/2025,PAUL & MALLORY'S NF WA,217.70,,5401.23
12/28/2025,TIM HORTONS #1551,25.59,,5183.53
12/26/2025,TIM HORTONS #0450,2.61,,5157.94
12/25/2025,Netflix.com,21.46,,5155.33'''

    data = {
        'file': (io.BytesIO(csv_content.encode()), 'test.csv')
    }

    response = client.post(
        '/api/expenses/parse-csv',
        data=data,
        headers=get_auth_header(),
        content_type='multipart/form-data'
    )

    assert response.status_code == 200
    data = response.json

    # Should parse 4 expenses
    assert data['total_parsed'] == 4
    assert len(data['expenses']) == 4

    # Check first expense
    assert data['expenses'][0]['date'] == '2025-12-28'
    assert data['expenses'][0]['description'] == "PAUL & MALLORY'S NF WA"
    assert data['expenses'][0]['amount'] == 217.70


def test_parse_csv_mixed_formats(client, setup_test_data):
    """Test parsing CSV with mixed date formats in same file."""
    csv_content = '''"2025-12-01","ENBRIDGE GAS A4A6W8","79.75",,"8695.15"
12/28/2025,TIM HORTONS #1551,25.59,,5183.53'''

    data = {
        'file': (io.BytesIO(csv_content.encode()), 'test.csv')
    }

    response = client.post(
        '/api/expenses/parse-csv',
        data=data,
        headers=get_auth_header(),
        content_type='multipart/form-data'
    )

    assert response.status_code == 200
    data = response.json

    # Should parse both expenses
    assert data['total_parsed'] == 2


def test_parse_csv_skip_money_in_transactions(client, setup_test_data):
    """Test that money_in transactions are skipped."""
    csv_content = '''"2025-12-01","SEND E-TFR ***sG3","36",,"7774.9"
"2025-12-01","PTS FRM: 05966297412",,"1000","8774.9"
"2025-12-01","PAYCHECK DEPOSIT",,"2000","10774.9"
"2025-12-01","ENBRIDGE GAS A4A6W8","79.75",,"8695.15"'''

    data = {
        'file': (io.BytesIO(csv_content.encode()), 'test.csv')
    }

    response = client.post(
        '/api/expenses/parse-csv',
        data=data,
        headers=get_auth_header(),
        content_type='multipart/form-data'
    )

    assert response.status_code == 200
    data = response.json

    # Should only parse 2 expenses (skip the 2 money_in transactions)
    assert data['total_parsed'] == 2
    assert data['expenses'][0]['description'] == 'SEND E-TFR ***sG3'
    assert data['expenses'][1]['description'] == 'ENBRIDGE GAS A4A6W8'


def test_parse_csv_invalid_date_format(client, setup_test_data):
    """Test handling of invalid date formats."""
    csv_content = '''"INVALID-DATE","SOME EXPENSE","100",,"1000"
"2025-12-01","VALID EXPENSE","50",,"950"'''

    data = {
        'file': (io.BytesIO(csv_content.encode()), 'test.csv')
    }

    response = client.post(
        '/api/expenses/parse-csv',
        data=data,
        headers=get_auth_header(),
        content_type='multipart/form-data'
    )

    assert response.status_code == 200
    data = response.json

    # Should parse 1 valid expense
    assert data['total_parsed'] == 1
    assert data['total_errors'] == 1

    # Check error details
    assert 'Invalid date format' in data['errors'][0]['error']


def test_parse_csv_invalid_amount(client, setup_test_data):
    """Test handling of invalid amounts."""
    csv_content = '''"2025-12-01","BAD AMOUNT","NOT_A_NUMBER",,"1000"
"2025-12-01","VALID EXPENSE","50.25",,"950"'''

    data = {
        'file': (io.BytesIO(csv_content.encode()), 'test.csv')
    }

    response = client.post(
        '/api/expenses/parse-csv',
        data=data,
        headers=get_auth_header(),
        content_type='multipart/form-data'
    )

    assert response.status_code == 200
    data = response.json

    # Should parse 1 valid expense
    assert data['total_parsed'] == 1
    assert data['total_errors'] == 1

    # Check error details
    assert 'Invalid amount' in data['errors'][0]['error']


def test_parse_csv_empty_rows(client, setup_test_data):
    """Test that empty rows are skipped."""
    csv_content = '''"2025-12-01","EXPENSE 1","100",,"1000"

"2025-12-02","EXPENSE 2","50",,"950"
,,,
"2025-12-03","EXPENSE 3","25",,"925"'''

    data = {
        'file': (io.BytesIO(csv_content.encode()), 'test.csv')
    }

    response = client.post(
        '/api/expenses/parse-csv',
        data=data,
        headers=get_auth_header(),
        content_type='multipart/form-data'
    )

    assert response.status_code == 200
    data = response.json

    # Should parse 3 expenses, skipping empty rows
    assert data['total_parsed'] == 3


def test_parse_csv_no_file_provided(client, setup_test_data):
    """Test error when no file is provided."""
    response = client.post(
        '/api/expenses/parse-csv',
        data={},
        headers=get_auth_header(),
        content_type='multipart/form-data'
    )

    assert response.status_code == 400
    assert 'No file provided' in response.json['error']


def test_parse_csv_invalid_file_type(client, setup_test_data):
    """Test error when file is not a CSV."""
    data = {
        'file': (io.BytesIO(b'test content'), 'test.txt')
    }

    response = client.post(
        '/api/expenses/parse-csv',
        data=data,
        headers=get_auth_header(),
        content_type='multipart/form-data'
    )

    assert response.status_code == 400
    assert 'File must be a CSV' in response.json['error']


def test_parse_csv_requires_authentication(client, setup_test_data):
    """Test that CSV parsing requires authentication."""
    csv_content = '''"2025-12-01","EXPENSE","100",,"1000"'''

    data = {
        'file': (io.BytesIO(csv_content.encode()), 'test.csv')
    }

    response = client.post(
        '/api/expenses/parse-csv',
        data=data,
        content_type='multipart/form-data'
    )

    assert response.status_code == 401


def test_parse_csv_line_numbers_tracking(client, setup_test_data):
    """Test that line numbers are tracked correctly."""
    csv_content = '''"2025-12-01","EXPENSE 1","100",,"1000"
"2025-12-02","EXPENSE 2","50",,"950"
"2025-12-03","EXPENSE 3","25",,"925"'''

    data = {
        'file': (io.BytesIO(csv_content.encode()), 'test.csv')
    }

    response = client.post(
        '/api/expenses/parse-csv',
        data=data,
        headers=get_auth_header(),
        content_type='multipart/form-data'
    )

    assert response.status_code == 200
    data = response.json

    # Check that line numbers are sequential
    assert data['expenses'][0]['line'] == 1
    assert data['expenses'][1]['line'] == 2
    assert data['expenses'][2]['line'] == 3


def test_parse_csv_decimal_amounts(client, setup_test_data):
    """Test parsing of decimal amounts."""
    csv_content = '''"2025-12-01","EXPENSE 1","100.50",,"1000"
"2025-12-02","EXPENSE 2","0.99",,"950"
"2025-12-03","EXPENSE 3","1234.56",,"925"'''

    data = {
        'file': (io.BytesIO(csv_content.encode()), 'test.csv')
    }

    response = client.post(
        '/api/expenses/parse-csv',
        data=data,
        headers=get_auth_header(),
        content_type='multipart/form-data'
    )

    assert response.status_code == 200
    data = response.json

    assert data['expenses'][0]['amount'] == 100.50
    assert data['expenses'][1]['amount'] == 0.99
    assert data['expenses'][2]['amount'] == 1234.56
