with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    'fillcolor=color + "33",',
    'fillcolor="rgba({},{},{},0.2)".format(int(color[1:3],16), int(color[3:5],16), int(color[5:7],16)),'
)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Done — restart Streamlit now")
