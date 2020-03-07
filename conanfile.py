import os
import subprocess
import shutil
from conans import ConanFile, tools, errors

def Python3ConanFile():
    class _Python3ConanFile(ConanFile):
        #def build_requirements(self):
        #    self.build_requires("python3/3.7.3@kwallner/stable")
        #
        #def requirements(self):
        #    pass
        @property
        def python_command(self):
            import os
            for python3_bin_dir in self.deps_cpp_info["python-base"].bin_paths:
                self.output.info("Searching for python-base in directory \"%s\"." % python3_bin_dir)
                python_exe = os.path.join(python3_bin_dir, "python3%s" % (".exe" if tools.os_info.is_windows else ""))
                if os.path.isfile(python_exe):
                    self.output.info("Found python3 executable as \"%s\"." % python_exe)
                    return python_exe
                python_exe = os.path.join(python3_bin_dir, "python%s" % (".exe" if tools.os_info.is_windows else ""))
                if os.path.isfile(python_exe):
                    self.output.info("Found python3 executable as \"%s\"." % python_exe)
                    return python_exe
            raise errors.ConanInvalidConfiguration("python interpreter not found.")
        
        def python_run(self, *argv, **kwargs):
            import subprocess 
            command= [ self.python_command ]
            for arg in argv: command.append(arg) 
            self.output.info("Executing python3 (cwd=%s): %s" % (os.getcwd(), " ".join(command)))
            subprocess.run(command, **kwargs)
    return _Python3ConanFile

class ConanProject(ConanFile):
    name        = "python-base"
    version     = "3.7.6"
    url         = ""
    license     = "Python Software Foundation License Version 2"
    description = "Python Programming Language Version 3"
    settings = "os", "arch"
    generators  = "txt"
    no_copy_source = True
    _pip_whl = "pip-20.0.2-py2.py3-none-any.whl"

    @property
    def python_interpreter(self):
        return "python.exe" if self.settings.os == "Windows" else "./bin/python3"

    def source(self):
        if self.settings.os == "Windows":
            if self.settings.arch == "x86":
                tools.download("https://www.python.org/ftp/python/3.7.6/python-3.7.6-embed-win32.zip", "python.zip", md5="accb8a137871ec632f581943c39cb566")
            elif self.settings.arch == "x86_64":
                tools.download("https://www.python.org/ftp/python/3.7.6/python-3.7.6-embed-amd64.zip", "python.zip", md5="5f84f4f62a28d3003679dc693328f8fd")
            else:
                raise errors.ConanInvalidConfiguration("Invalid architecture \"%s\" for os \"%s\"." % (self.settings.arch, self.settings.os))
        else:
            raise errors.ConanInvalidConfiguration("Unsupported os \"%s\"." % (self.settings.os))
        tools.download("https://files.pythonhosted.org/packages/54/0c/d01aa759fdc501a58f431eb594a17495f15b88da142ce14b5845662c13f3/%s" % self._pip_whl, self._pip_whl, sha256="4ae14a42d8adba3205ebeb38aa68cfc0b6c346e1ae2e699a0b3bad4da19cef5c")

    def _install_pip(self):
        self.output.info("Installing pip from package \"%s\" to folder \"%s\"." % (self._pip_whl, self.build_folder))
        shutil.copyfile(os.path.join(self.source_folder, self._pip_whl), self._pip_whl)
        with tools.chdir(self.build_folder):
            env_python = os.environ.copy()
            env_python["PYTHONPATH"] = self.build_folder
            subprocess.run([self.python_interpreter, "%s/pip" % self._pip_whl, "install", "--no-index", "--no-cache-dir", "--isolated", "--find-links=%s" % self.source_folder, self._pip_whl], cwd=self.build_folder, shell=True, check=True, env=env_python)
        os.remove(self._pip_whl)
       
    def build(self):
        if self.settings.os == "Windows":
            tools.unzip(os.path.join(self.source_folder, "python.zip"), self.build_folder)
            os.remove("python37._pth")
        else:
            raise errors.ConanInvalidConfiguration("Unsupported os \"%s\"." % (self.settings.os))
        self._install_pip()
        shutil.copytree(self.build_folder, self.package_folder, ignore=shutil.ignore_patterns('__pycache__', 'Scripts'))
        
    def package(self):
        pass

    def package_info(self):
        self.cpp_info.includedirs = ['include']
        self.cpp_info.libdirs = ['lib']
        self.env_info.PYTHONPATH = self.package_folder
        if self.settings.os == "Windows":
            self.cpp_info.bindirs = ['.', 'Scripts']
            self.env_info.path.insert(0, self.package_folder)
            self.env_info.path.insert(0, os.path.join(self.package_folder, "Scripts"))
        else:
            self.cpp_info.bindirs = ['bin']
            self.env_info.path.insert(0, os.path.join(self.package_folder, "bin"))