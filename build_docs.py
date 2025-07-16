import subprocess

subprocess.run([
    "pdoc",
    "src",
    "--output-dir", "docs",
    "--docformat", "google",
])
