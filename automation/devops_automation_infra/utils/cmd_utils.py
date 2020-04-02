def convert_kwargs_to_options_string(kwargs, format_with_equals_sign=False):
    result_string = ""
    try:
        for k, v in kwargs.items():
            if format_with_equals_sign:
                result_string += f"--{k}={v} "
            else:
                result_string += f"--{k} {v} "
        return result_string
    except AttributeError:
        return kwargs

