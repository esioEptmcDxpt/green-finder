import time


def my_logger(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        print(f"関数{func.__name__}の実行時間は{time.time() - start}")
        return result

    return wrapper