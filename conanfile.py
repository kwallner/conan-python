import os
import subprocess
import shutil
from conans import ConanFile, VisualStudioBuildEnvironment, tools, errors, AutoToolsBuildEnvironment
    
class ConanProject(ConanFile):
    name        = "python"
    version     = "3.7.6"
    url         = ""
    license     = "Python Software Foundation License Version 2"
    description = "Python Programming Language Version 3"
    settings = "os", "arch", "compiler"
    generators  = "txt"
    _pip_whl = "pip-20.0.2-py2.py3-none-any.whl"

    @property
    def python_interpreter(self):
        return "bin\\python.exe" if self.settings.os == "Windows" else "./bin/python3"

    def configure(self):
        if self.settings.os == "Windows":
            if self.settings.arch != "x86_64":
                raise errors.ConanInvalidConfiguration("Platform is not supported.")

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
        if self.settings.os == "Windows":
            env_build = VisualStudioBuildEnvironment(self)
            with tools.environment_append(env_build.vars):
                with tools.chdir(os.path.join("Python-%s" % self.version, "PCBuild")):
                    vcvars = tools.vcvars_command(self.settings)
                    self.run("%s && cmd /C build.bat -p x64 -d" % vcvars)
                    self.run("%s && cmd /C build.bat -p x64" % vcvars)
                #subprocess.run(["cmd", "/C", "build.bat", "-p", "x64", "-d"], check=True, cwd=os.path.join(self.build_folder, "Python-%s" % self.version, "PCBuild"))
                #    #msbuild = MSBuild(self)
                #    #msbuild.build("pcbuild.sln", build_type="Debug", arch ="x86_64")
                #    #msbuild.build("pcbuild.sln", build_type="Release")
        else:
            with tools.chdir("Python-%s" % self.version):
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
                args = [] # ["--enable-shared"] if self.options.shared else []
                atools.configure(args=args)
                atools.make()
                atools.install()
        
    def package(self):
        if self.settings.os == "Windows":
            out_folder = {"x86_64": "amd64", "x86": "win32"}.get(str(self.settings.arch))
            pcbuild_folder = os.path.join(self.build_folder, "Python-%s" % self.version, "PCBuild", out_folder)
            pc_folder = os.path.join(self.build_folder, "Python-%s" % self.version, "PC")
            self.copy(pattern="*.dll", dst="bin", src=pcbuild_folder, keep_path=False)
            self.copy(pattern="*.exe", dst="bin", src=pcbuild_folder, keep_path=False)
            self.copy(pattern="*.lib", dst="libs", src=pcbuild_folder, keep_path=False)
            self.copy(pattern="*.pyd", dst="DLLs", src=pcbuild_folder, keep_path=False)
            shutil.copytree(os.path.join(self.build_folder, "Python-%s" % self.version, "Include"), os.path.join(self.package_folder, "include"))
            self.copy(pattern="*.h", dst="include", src=pc_folder, keep_path=False)
            shutil.copytree(os.path.join(self.build_folder, "Python-%s" % self.version, "Lib"), os.path.join(self.package_folder, "Lib"))
        self._install_pip()

    def package_id(self):
        del self.info.settings.compiler
        
    def package_info(self):
        self.cpp_info.includedirs = ['include']
        self.cpp_info.libdirs = ['libs']
        self.cpp_info.bindirs = ['bin']
        self.env_info.PATH.insert(0, os.path.join(self.package_folder, "bin"))
        self.env_info.PYTHONPATH.insert(0, os.path.join(self.package_folder, "Lib"))
        self.env_info.PYTHONPATH.insert(0, os.path.join(self.package_folder, "Lib", "site-packages"))
        self.env_info.PYTHONHOME = self.package_folder
