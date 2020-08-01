import os
import sys
import glob
import subprocess
import tempfile
import shutil
from conans import ConanFile, VisualStudioBuildEnvironment, tools, errors, AutoToolsBuildEnvironment
    
class PythonHelper(object):
    _install_packages = []

    @property 
    def _python_command(self):
        python_cmd = shutil.which("python3")
        if python_cmd is None:
            python_cmd = shutil.which("python")
        if python_cmd is None:
            raise errors.ConanInvalidConfiguration("Failed to find python executable.")
        return python_cmd
    
    def python_run(self, args, *, append_pythonpath=[], **kwargs):
        pythonpath_list = append_pythonpath if type(append_pythonpath) == list else [ str(append_pythonpath) ] 
        python_environ = os.environ
        python_environ["PYTHONPATH"] = os.pathsep.join([ str(p) for p in pythonpath_list ]) + os.pathsep + os.environ["PYTHONPATH"]
        command = [self._python_command]
        command.extend(args)
        return subprocess.run(command, **kwargs, env=python_environ)
   
    @property
    def _python_version(self):
        python_version_output = None
        try:
            python_version_output = subprocess.check_output([self._python_command, "-V"])
        except:
            raise errors.ConanInvalidConfiguration("Failed to detect python version.")
        (_,python_version_output_decoded) = python_version_output.decode("utf8").strip().split(" ", 2) 
        return ("".join(python_version_output_decoded.split(".")[0:2]))

    @property
    def _python_platform(self):
        if self.settings.os == 'Windows':
            if self.settings.arch == 'x86_64':
                return "win_amd64"
            elif self.settings.arch == 'x86':   
                return  "win_x86"
        elif self.settings.os == 'Linux':
            if self.settings.arch == 'x86_64':
                return "linux_x86_64"
            elif self.settings.arch == 'x86':   
                return "linux_x86"
            elif self.settings.arch == 'aarch64':   
                return "linux_aarch64"
        raise errors.ConanInvalidConfiguration("Failed to detect python platform.")

    @property
    def _python_implementation(self):
        return "cp"

    @property
    def _python_platform_version_implementation(self):
        platform_spec = []
        if not self._python_platform == "linux_x86_64":
            platform_spec.extend(["--platform", self._python_platform])
        platform_spec.extend(["--python-version", self._python_version])
        platform_spec.extend(["--implementation", self._python_implementation])
        return platform_spec

    def _append_install_package(self, package_spec):
        if not package_spec in self._install_packages:
            self._install_packages.append(package_spec)
   
    def _pypi_pip_to_archive(self, pkg_name):
        import subprocess
        args = [
            "-m", "pip",
            "--disable-pip-version-check",
            "download",
            "--only-binary=:all:",
            "--no-binary=:none:" ]
        args.extend(self._python_platform_version_implementation)
        args.extend([ 
            "--find-links=.", 
            "--isolated", 
            pkg_name ])
        self.python_run(args, cwd=self.source_folder, check=True)
        
    def pip_add_whl(self, pkg_name):
        self._pypi_pip_to_archive(pkg_name)
        self._append_install_package(pkg_name)
    
    def pip_add_tar(self, pkg_name, setup_args=[]):
        with tempfile.TemporaryDirectory() as tmpdirname:
            with tools.chdir(tmpdirname): 
                args = [
                    "-m", "pip",
                    "--disable-pip-version-check",
                    "download",
                    "--no-deps"]
                args.extend(self._python_platform_version_implementation)
                args.extend(["--find-links=.", 
                    "--isolated", 
                    pkg_name])
                self.output.info("-- running python (cwd=%s) with args: %s" % (".", " ".join(args))) 
                self.python_run(args, check=True)
                for filename in os.listdir("."):
                    if filename.endswith(".tar.gz"):
                        tools.untargz(filename)
                        with tools.chdir(filename.replace(".tar.gz", "")): 
                            tools.replace_in_file("setup.py", "from distutils.core import setup", "from setuptools import setup", strict=False)
                            args = [ "setup.py" ]
                            args.extend(setup_args)
                            args.extend(["bdist_wheel", "-d", self.source_folder])
                            self.output.info("-- running python (cwd=%s) with args: %s" % (".", " ".join(args))) 
                            self.python_run(args, check=True)
                        self._append_install_package(pkg_name)
                    else:
                        pass
                       
    def pip_run_install(self):
        os.linesep = '\n'
        with open("requirements.txt", "w") as f:
            for package in self._install_packages:
               f.write('%s\n' % package)
        args = [
            "-m", "pip",
            "install",
            "--no-index",
            "--no-cache-dir", 
            "--no-compile",
            "--isolated",
            "--upgrade",
            "--upgrade-strategy", "eager",
            "--find-links=%s" % self.source_folder, 
            "--target", self.package_folder.replace("\\", "/"),
            "-r", "requirements.txt"]
        self.python_run(args, check=True)
        shutil.rmtree(os.path.join(self.package_folder, "bin"))

    @property
    def _python_system_spec(self):
        return self._python_implementation + self._python_version + "-" + self._python_platform

    def pip_make_installer(self, output_directory=None, zip_directory=None, zip_filename=None):
        if output_directory is None:
            output_directory = self.package_folder
        if zip_filename is None:
            zip_filename = self.name + "-" + self.version + "-" + self._python_system_spec
        if zip_directory is None:
            zip_directory = self.name + "-" + self.version
        os.linesep = '\n'
        with open("requirements.txt", "w") as f:
            for package in self._install_packages:
               f.write('%s\n' % package)
        with open("install.sh", "w") as f:
            f.write('#!/bin/sh\n')
            f.write('set -e\n')
            f.write('\n')
            f.write('echo "Installing packages:"\n')
            f.write('%s -m pip install --quiet --no-index --no-cache-dir --isolated --upgrade --upgrade-strategy eager --find-links=. -r %s\n' % (self._python_command, "requirements.txt"))
            f.write('\n')
        os.chmod("install.sh", 0o775)
        if self.settings.os == "Windows":
            os.linesep = '\r\n'
            with open("install.bat", "w") as f:
                f.write('@echo off\n')
                f.write('\n')
                f.write('echo Installing packages:\n')
                f.write('%s -m pip install --quiet --no-index --no-cache-dir --isolated --upgrade --upgrade-strategy eager --find-links=. -r %s\n' % (self._python_command, "requirements.txt"))
                f.write('\n')
        os.chmod("install.bat", 0o775)
        os.makedirs(output_directory, exist_ok=True)
        from zipfile import ZipFile
        with ZipFile(os.path.join(output_directory, zip_filename + '.zip'), 'w') as zip:
            zip.write("requirements.txt", arcname=zip_directory + "/" + "requirements.txt")
            zip.write("install.sh", arcname=zip_directory + "/" + "install.sh")
            if self.settings.os == "Windows":
                zip.write("install.bat", arcname=zip_directory + "/" + "install.bat")
            for whl_file in [ f for f in os.listdir(".") if f.endswith(".whl") ]:
                zip.write(whl_file, arcname=zip_directory + "/" + whl_file)
                       
class ConanProject(ConanFile):
    name        = "python"
    version     = "3.7.8"
    url         = ""
    license     = "Python Software Foundation License Version 2"
    description = "Python Programming Language Version 3"
    settings = "os", "arch"
    generators  = "txt"
    _pip_whl = "pip-20.1.1-py2.py3-none-any.whl"
    _wheel_whl = "wheel-0.34.2-py2.py3-none-any.whl"
    _setuptools_whl = "setuptools-47.3.1-py3-none-any.whl"

    @property
    def python_interpreter(self):
        if self.settings.os == "Windows":
            return os.path.join(self.package_folder, "python.exe")
        else:
            return os.path.join(self.package_folder, "bin", "python3")

    def build_requirements(self):
        self.build_requires("cpython/%s@%s/%s" % (self.version, self.user, self.channel))

    def source(self):
        tools.download("https://files.pythonhosted.org/packages/43/84/23ed6a1796480a6f1a2d38f2802901d078266bda38388954d01d3f2e821d/%s" % self._pip_whl, self._pip_whl, sha256="b27c4dedae8c41aa59108f2fa38bf78e0890e590545bc8ece7cdceb4ba60f6e4")
        tools.download("https://files.pythonhosted.org/packages/8c/23/848298cccf8e40f5bbb59009b32848a4c38f4e7f3364297ab3c3e2e2cd14/%s" % self._wheel_whl, self._wheel_whl, sha256="df277cb51e61359aba502208d680f90c0493adec6f0e848af94948778aed386e")
        tools.download("https://files.pythonhosted.org/packages/e9/93/4860cebd5ad3ff2664ad3c966490ccb46e3b88458b2095145bca11727ca4/%s" % self._setuptools_whl, self._setuptools_whl, sha256="4ba6f9789ea243a6b8ba57da81f75a53494456117810436fd9277a74d1c915d1")
        
    def _install_pip(self, whl_file):
        with tools.chdir(self.package_folder):
            shutil.copyfile(os.path.join(self.build_folder, self._pip_whl), os.path.join(self.package_folder, self._pip_whl))
            self.output.info("Installing pip from package \"%s\" to folder \"%s\"." % (self._pip_whl, self.package_folder))
            env_python = os.environ.copy()
            env_python["PYTHONPATH"] = self.package_folder
            subprocess.run([self.python_interpreter,
                "%s/pip" % self._pip_whl,
                "install", 
                "--no-index", 
                "--no-cache-dir", 
                "--isolated", 
                "--find-links=%s" % self.build_folder, 
                "--prefix=.", 
                "--no-warn-script-location", 
                whl_file], cwd=self.package_folder, shell=(self.settings.os == "Windows"), check=True, env=env_python) 
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
                "--find-links=%s" % self.build_folder, 
                "--prefix=.", 
                "--no-warn-script-location", 
                whl_file], cwd=self.package_folder, shell=(self.settings.os == "Windows"), check=True, env=env_python)

    def build(self):
        from distutils.dir_util import copy_tree
        copy_tree(self.deps_cpp_info["cpython"].rootpath, self.package_folder)

    def package(self):
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
        if self.settings.os == "Windows":
            self.cpp_info.bindirs = ['.']
        else:
            self.cpp_info.bindirs = ['bin']
        if self.settings.os == "Windows":
            self.env_info.PATH.insert(0, self.package_folder)
        else:
            self.env_info.PATH.insert(0, os.path.join(self.package_folder, "bin"))
        self.env_info.PYTHONPATH.insert(0, os.path.join(self.package_folder, "Lib"))
        self.env_info.PYTHONPATH.insert(0, os.path.join(self.package_folder, "Lib", "site-packages"))
        self.env_info.PYTHONHOME = self.package_folder
