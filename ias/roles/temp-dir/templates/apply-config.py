import os, re
import subprocess

fileList = os.listdir(".")

for fileName in fileList:
    if not re.match(".*\.yaml$", fileName): continue
    subprocess.call(["KUBECONFIG=~/.kube/admin.conf kubectl apply -f {}".format(fileName)], shell=True)
