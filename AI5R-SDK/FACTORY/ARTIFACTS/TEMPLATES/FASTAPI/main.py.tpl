from fastapi import FastAPI

app = FastAPI(title="{{project_name}}")

@app.get("/")
def root():
    return {"status":"ok"}
