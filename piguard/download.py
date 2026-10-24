"""Fetch Kaggle datasets, Kaggle benchmark models and the InjecAgent benchmark."""
import shutil
import urllib.request

from . import config as C


def download_datasets(force=False):
    import kagglehub

    for handle, (folder, files) in C.KAGGLE_DATASETS.items():
        dest = C.DATA_RAW / folder
        if not force and all((dest / f).exists() for f in files):
            print(f"[data] {handle}: cached")
            continue
        src = kagglehub.dataset_download(handle)
        for f in files:
            (dest / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f"{src}/{f}", dest / f)
        print(f"[data] {handle}: downloaded -> {dest}")


def download_injecagent(force=False):
    C.INJECAGENT_DIR.mkdir(parents=True, exist_ok=True)
    for f in C.INJECAGENT_FILES:
        dest = C.INJECAGENT_DIR / f
        if dest.exists() and not force:
            continue
        urllib.request.urlretrieve(C.INJECAGENT_URL + f, dest)
    print(f"[data] InjecAgent -> {C.INJECAGENT_DIR}")


def model_path(name):
    """Local path of a Kaggle benchmark model, downloading on first use. None if unavailable."""
    import kagglehub

    try:
        return kagglehub.model_download(C.KAGGLE_MODELS[name])
    except Exception as e:  # gated model without credentials, offline, ...
        local = sorted((C.CACHE_DIR / "kagglehub" / "models" / C.KAGGLE_MODELS[name]).glob("*/config.json"))
        if local:  # offline: use the copy already cached inside the project
            return str(local[-1].parent)
        print(f"[model] {name} unavailable ({type(e).__name__}: {str(e)[:120]})")
        return None


def download_all():
    download_datasets()
    download_injecagent()
    for name in C.KAGGLE_MODELS:
        p = model_path(name)
        print(f"[model] {name}: {p}")
