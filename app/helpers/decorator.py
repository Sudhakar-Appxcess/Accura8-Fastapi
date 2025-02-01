from logzero import logger


def db(action: str):
    """
    Decorator to perform DB Commit on success and
    Rollback on failure or exception.

    Args:
        action (str): Action Performed ex. hold, unhold, stock_add .etc
    """
    def wrap(func):
        def decor(self, *arg, **kwarg):
            try:
                method_output = func(self, *arg, **kwarg)
                self.s.commit()
            except Exception as e:
                self.s.rollback()
                logger.error(f'Error {str(e)} on {
                             action.title()} | /n {str(arg)}', e)
            return method_output
        return decor
    return wrap


def response(func):
    def wrapper(*args):
        res = func(*args)
        if type(res) is not list:
            return res.__dict__
        else:
            try:
                return [r.__dict__ for r in res]
            except Exception as e:
                logger.error(f'Error {str(e)} on Extract Response {str(res)}'
                             ", But returining raw response", e)
                return res
    return wrapper
