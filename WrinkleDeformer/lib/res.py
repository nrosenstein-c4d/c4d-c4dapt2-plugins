import os, c4d
PROJECT_PATH = None
RESOURCE = None

def init(pypfile, resource):
    global PROJECT_PATH, RESOURCE
    PROJECT_PATH = os.path.dirname(pypfile)
    RESOURCE = resource

def string(name, *subst):
    result = RESOURCE.LoadString(globals()[name])
    for item in subst:
        result = result.replace('#', item, 1)
    return result

def tup(name, *subst):
    return (globals()[name], string(name, *subst))

def file(*parts):
    return os.path.join(PROJECT_PATH, *parts)

def bitmap(*parts):
    bitmap = c4d.bitmaps.BaseBitmap()
    result, ismovie = bitmap.InitWith(file(*parts))
    if result != c4d.IMAGERESULT_OK: return None
    return bitmap

WRINKLEDEFORMER_NAME       = 10000
WRINKLEDEFORMER_ACTIONTEXT = 10001

NR_WRINKLEDEFORMER_SEED       = 1000
NR_WRINKLEDEFORMER_ITERATIONS = 1001
Onr_wrinkledeformer           = 1033765
