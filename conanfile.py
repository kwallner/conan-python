import os
import glob
import subprocess
import shutil
from conans import ConanFile, VisualStudioBuildEnvironment, tools, errors, AutoToolsBuildEnvironment
    
class ConanProject(ConanFile):
    name        = "python"
    version     = "3.7.7"
    url         = ""
    license     = "Python Software Foundation License Version 2"
    description = "Python Programming Language Version 3"
    settings = "os", "arch"
    generators  = "txt"
    no_copy_source = True
    _pip_whl = "pip-20.0.2-py2.py3-none-any.whl"
    _wheel_whl = "wheel-0.34.2-py2.py3-none-any.whl"
    _setuptools_whl = "setuptools-46.0.0-py3-none-any.whl"

    @property
    def python_interpreter(self):
        return "bin\\python.exe" if self.settings.os == "Windows" else "./bin/python3"
            
    def build_requirements(self):
        self.build_requires("cpython/%s@%s/%s" % (self.version, self.user, self.channel))

    def source(self):
        tools.download("https://files.pythonhosted.org/packages/54/0c/d01aa759fdc501a58f431eb594a17495f15b88da142ce14b5845662c13f3/%s" % self._pip_whl, self._pip_whl, sha256="4ae14a42d8adba3205ebeb38aa68cfc0b6c346e1ae2e699a0b3bad4da19cef5c")
        tools.download("https://files.pythonhosted.org/packages/8c/23/848298cccf8e40f5bbb59009b32848a4c38f4e7f3364297ab3c3e2e2cd14/%s" % self._wheel_whl, self._wheel_whl, sha256="df277cb51e61359aba502208d680f90c0493adec6f0e848af94948778aed386e")
        tools.download("https://files.pythonhosted.org/packages/70/b8/b23170ddda9f07c3444d49accde49f2b92f97bb2f2ebc312618ef12e4bd6/%s" % self._setuptools_whl, self._setuptools_whl, sha256="693e0504490ed8420522bf6bc3aa4b0da6a9f1c80c68acfb4e959275fd04cd82")

    def _install_pip(self, whl_file):
        with tools.chdir(self.package_folder):
            shutil.copyfile(os.path.join(self.source_folder, self._pip_whl), os.path.join(self.package_folder, self._pip_whl))
            self.output.info("Installing pip from package \"%s\" to folder \"%s\"." % (self._pip_whl, self.package_folder))
            env_python = os.environ.copy()
            env_python["PYTHONPATH"] = self.package_folder
            subprocess.run([self.python_interpreter, 
                "%s/pip" % self._pip_whl, 
                "install", 
                "--no-index", 
                "--no-cache-dir", 
                "--isolated", 
                "--find-links=%s" % self.source_folder, 
                "--prefix=.", 
                "--no-warn-script-location", 
                whl_file], cwd=self.package_folder, shell=True, check=True, env=env_python)
            os.remove(os.path.join(self.package_folder, self._pip_whl))
        
    def _install_whl(self, whl_file):
        with tools.chdir(self.package_folder):
            self.output.info("Installing pip from package \"%s\" to folder \"%s\"." % (whl_file, self.package_folder))
            env_python = os.environ.copy()
            env_python["PYTHONPATH"] = self.package_folder
            subprocess.run([self.python_interpreter, 
                "-m", "pip", 
                "install", 
                "--no-index", 
                "--no-cache-dir", 
                "--isolated", 
                "--find-links=%s" % self.source_folder, 
                "--prefix=.", 
                "--no-warn-script-location", 
                whl_file], cwd=self.package_folder, shell=True, check=True, env=env_python)
            
    def build(self):
        if os.path.isdir(self.package_folder):
            shutil.rmtree(self.package_folder)
        shutil.copytree(self.deps_cpp_info["cpython"].rootpath, self.package_folder)
        self._install_pip("pip")
        self._install_whl("wheel")
        self._install_whl("setuptools")
        # Remove python compiled files
        for filename in glob.glob(os.path.join(self.package_folder, "**", "*.pyc"), recursive=True):
            os.remove(filename)
        for filename in glob.glob(os.path.join(self.package_folder, "**", "__pycache__"), recursive=True):
            os.rmdir(filename)
        
    def package_info(self):
        self.cpp_info.includedirs = ['include']
        self.cpp_info.libdirs = ['libs']
        self.cpp_info.bindirs = ['bin']
        self.env_info.PATH.insert(0, os.path.join(self.package_folder, "bin"))
        self.env_info.PYTHONPATH.insert(0, os.path.join(self.package_folder, "Lib"))
        self.env_info.PYTHONPATH.insert(0, os.path.join(self.package_folder, "Lib", "site-packages"))
        self.env_info.PYTHONHOME = self.package_folder
