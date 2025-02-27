from datetime import datetime

# NOTE: dir[`/images/avatar/`] => path[`/images/avatar/`]
def path_from_dir(dir):
    return f"/{dir}"

def strfnow():
    return datetime.now().strftime("%Y%m%d%H%M%S%f")