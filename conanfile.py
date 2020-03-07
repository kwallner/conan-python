import os
import subprocess
import shutil
from conans import ConanFile, MSBuild, tools, errors, AutoToolsBuildEnvironment

def Python3ConanFile():
    class _Python3ConanFile(ConanFile):
        #def build_requirements(self):
        #    self.build_requires("python3/3.7.6@akw/testing")
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
    name        = "python"
    version     = "3.7.6"
    url         = ""
    license     = "Python Software Foundation License Version 2"
    description = "Python Programming Language Version 3"
    settings = "os", "arch", "compiler", "build_type"
    generators  = "txt"
    _pip_whl = "pip-20.0.2-py2.py3-none-any.whl"

    @property
    def python_interpreter(self):
        return "bin\\python.exe" if self.settings.os == "Windows" else "./bin/python3"

    def system_requirements(self):
        if self.settings.os == "Linux":
            pack_name = self.name
            installer = tools.SystemPackageTool()
            installer.install("libffi-dev") 
    
    def source(self):
        tools.download("https://www.python.org/ftp/python/%s/Python-%s.tgz" % (self.version, self.version), "Python-%s.tgz" % self.version, md5="3ef90f064506dd85b4b4ab87a7a83d44")
        tools.download("https://files.pythonhosted.org/packages/54/0c/d01aa759fdc501a58f431eb594a17495f15b88da142ce14b5845662c13f3/%s" % self._pip_whl, self._pip_whl, sha256="4ae14a42d8adba3205ebeb38aa68cfc0b6c346e1ae2e699a0b3bad4da19cef5c")
        tools.unzip("Python-%s.tgz" % self.version)
        if tools.os_info.is_windows:  
            with tools.chdir(os.path.join("Python-%s" % self.version, "PCBuild")):
                self.run("get_externals.bat")
        os.remove("Python-%s.tgz" % self.version)

    def _install_pip(self):
        with tools.chdir(self.package_folder):
            shutil.copyfile(os.path.join(self.source_folder, self._pip_whl), self._pip_whl)
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
                self._pip_whl], cwd=self.package_folder, shell=True, check=True, env=env_python)
            shutil.rmtree("Scripts")
            os.remove(self._pip_whl)
       
    def build(self):
        with tools.chdir("Python-%s" % self.version):
            if self.settings.os == "Windows":
                with tools.chdir("PCBuild"):
                    with tools.vcvars(self.settings) if self.settings.compiler == "Visual Studio" else tools.no_op():
                        msbuild = MSBuild(self)
                        msbuild.build("pcbuild.sln")
            else:
                os.chmod("configure", 
                    stat.S_IRUSR |
                    stat.S_IWUSR |
                    stat.S_IXUSR |
                    stat.S_IRGRP |
                    stat.S_IWGRP |
                    stat.S_IXGRP |
                    stat.S_IROTH |
                    stat.S_IXOTH 
                    )
                atools = AutoToolsBuildEnvironment(self)
                args = ["--enable-shared"] if self.options.shared else []
                atools.configure(args=args)
                atools.make()
                atools.install()
        
    def package(self):
        if self.settings.os == "Windows":
            out_folder = {"x86_64": "amd64", "x86": "win32"}.get(str(self.settings.arch))
            pcbuild_folder = os.path.join(self.build_folder, "Python-%s" % self.version, "PCBuild", out_folder)
            pc_folder = os.path.join(self.build_folder, "Python-%s" % self.version, "PC")
            self.copy(pattern="*.dll", dst="bin", src=pcbuild_folder, keep_path=False)
            self.copy(pattern="*.lib", dst="lib", src=pcbuild_folder, keep_path=False)
            self.copy(pattern="*.exe", dst="bin", src=pcbuild_folder, keep_path=False)
            shutil.copytree(os.path.join(self.build_folder, "Python-%s" % self.version, "Include"), os.path.join(self.package_folder, "include"))
            self.copy(pattern="*.h", dst="include", src=pc_folder, keep_path=False)
        self._install_pip()

    def package_id(self):
        del self.info.settings.compiler
        del self.info.settings.build_type
        
    def package_info(self):
        self.cpp_info.includedirs = ['include']
        self.cpp_info.libdirs = ['lib']
        self.env_info.PYTHONPATH = os.path.join(self.package_folder, "lib") + os.pathsep + os.path.join(self.package_folder, "lib", "site-packages") 
        self.cpp_info.bindirs = ['bin']
        self.env_info.path.insert(0, os.path.join(self.package_folder, "bin"))