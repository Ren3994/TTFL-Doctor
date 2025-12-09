
def check_internet_connection():
    import requests

    try:
        requests.get('https://clients3.google.com/generate_204', timeout=5)
        return True
    except:
        return False

if __name__ == '__main__':
    print(check_internet_connection())