from core.storage import save_trainers, load_trainers


save_trainers({
    "2679460": {
        "trainer": "/tmp/test.exe"
    }
})


print(load_trainers())
