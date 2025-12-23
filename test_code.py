# test_code.py
def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)

def process_data(data):
    result = []
    for i in range(len(data)):
        if data[i] > 0:
            result.append(data[i] * 2)
    return result

# Missing error handling
def divide_numbers(a, b):
    return a / b

# SQL injection vulnerability
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return execute_query(query)