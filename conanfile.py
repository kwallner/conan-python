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
    options = { "with_tkinter" : [False,True] }
    default_options = { "with_tkinter" : False }
    _pip_whl = "pip-20.1.1-py2.py3-none-any.whl"
    _wheel_whl = "wheel-0.34.2-py2.py3-none-any.whl"
    _setuptools_whl = "setuptools-47.1.1-py3-none-any.whl"

    @property
    def python_interpreter(self):
        return "bin\\python.exe" if self.settings.os == "Windows" else "./bin/python3"

    def configure(self):
        self.options["cpython"].with_tkinter = self.options.with_tkinter

    def build_requirements(self):
        self.build_requires("cpython/%s@%s/%s" % (self.version, self.user, self.channel))

    def source(self):
        tools.download("https://files.pythonhosted.org/packages/43/84/23ed6a1796480a6f1a2d38f2802901d078266bda38388954d01d3f2e821d/%s" % self._pip_whl, self._pip_whl, sha256="b27c4dedae8c41aa59108f2fa38bf78e0890e590545bc8ece7cdceb4ba60f6e4")
        tools.download("https://files.pythonhosted.org/packages/8c/23/848298cccf8e40f5bbb59009b32848a4c38f4e7f3364297ab3c3e2e2cd14/%s" % self._wheel_whl, self._wheel_whl, sha256="df277cb51e61359aba502208d680f90c0493adec6f0e848af94948778aed386e")
        tools.download("https://files.pythonhosted.org/packages/95/95/f657b6e17f00c3f35b5f68b10e46c3a43af353d8856bd57bfcfb1dbb3e92/%s" % self._setuptools_whl, self._setuptools_whl, sha256="74f33f44290f95c5c4a7c13ccc9d6d1a16837fe9dce0acf411dd244e7de95143")

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
