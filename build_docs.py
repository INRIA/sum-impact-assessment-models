import subprocess

subprocess.run([
    "pdoc",
    "src/sum_impact_assessment",
    "--output-dir", "docs",
    "--docformat", "google",
])
