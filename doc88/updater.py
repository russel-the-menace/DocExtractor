from .io_utils import *
import re
import shutil
import os
import json
import platform

class Update:
    def __init__(self, cfg2: Config) -> None:
        self.cfg2 = cfg2
        self.docs_dir = os.path.normpath(self.cfg2.o_dir_path)

    def get_ffdec_asset(self):
        """Return (rel, asset_name) where asset_name is the chosen ffdec zip asset or None."""
        try:
            rel = github_release(self.cfg2.ffdec_repo)
        except Exception as e:
            raise
        version = rel.latest_version.lstrip("v").lstrip("V")
        releases = rel.releases
        desired_name = f"ffdec_{version}.zip"
        asset_name = None
        if desired_name in releases:
            asset_name = desired_name
        else:
            candidates = []
            for name in releases:
                m = re.match(r'^ffdec_(\d+\.\d+\.\d+)\.zip$', name)
                if m:
                    candidates.append((name, m.group(1)))
            if candidates:
                candidates.sort(key=lambda x: tuple(int(y) for y in x[1].split('.')), reverse=True)
                asset_name = candidates[0][0]
        return rel, asset_name
    
    def download_ffdec(self):
        try:
            rel, asset_name = self.get_ffdec_asset()
        except Exception as e:
            print(f"ffdec release check failed: {e}")
            return False
        if not asset_name:
            print("ffdec asset not found.")
            return False
        ffdec_url = self.cfg2.proxy_url + rel.releases[asset_name]
        print("Downloading ffdec...")
        try:
            os.makedirs(self.cfg2.ffdec_dir)
        except FileExistsError:
            if choose("exists"):
                shutil.rmtree(self.cfg2.ffdec_dir)
                os.makedirs(self.cfg2.ffdec_dir)
            else:
                return False
        try:
            ffdec_zip = os.path.join(self.cfg2.ffdec_dir, "ffdec.zip")
            download(ffdec_url, ffdec_zip)
        except:
            print("Download failed. Check network or proxy_url.")
            input_break()
            return False
        print("Extracting ffdec...")
        try:
            extract(ffdec_zip, self.cfg2.ffdec_dir)
            os.remove(ffdec_zip)
            return True
        except zipfile.BadZipFile:
            print("Extract failed. Check ffdec_repo.")
            input_break()
            return False

    def check_java(self):
        try:
            output = subprocess.run(['java', '-version'], capture_output=True, text=True)
            if output.returncode != 0:
                print("Java not available.")
                return False
            return True
        except FileNotFoundError:
            platform = os.name
            if platform == "nt":
                java_home = os.environ.get("JAVA_HOME", "")
                if java_home:
                    java_path = os.path.join(java_home, "bin", "java.exe")
                    if os.path.isfile(java_path):
                        os.environ["PATH"] = os.pathsep.join([os.path.join(java_home, "bin"), os.environ.get("PATH", "")])
                        try:
                            if subprocess.run(['java', '-version'],capture_output=True).returncode == 0:
                                print("Java found via JAVA_HOME; consider adding to PATH.")
                                return True
                            else:
                                print("Java not available.")
                                return False
                        except FileNotFoundError:
                            print("Java not found.")
                            return False
                    else:
                        print("Java not found.")
                        return False
            else:
                print("Java not found.")
                return False

    def ffdec_update(self):
        ffdec_jar = os.path.join(self.cfg2.ffdec_dir, "ffdec.jar")
        if os.path.isfile(ffdec_jar):
            if choose("是否删除旧版本ffdec，否则创建备份？ (Y: 删除, N: 备份): "):
                try:
                        shutil.rmtree(self.cfg2.ffdec_dir)
                except Exception as e:
                    print(f"Error occurred while removing old version: {e}")
            else:
                try:
                    name=self.cfg2.ffdec_version
                    for i in range(1,100):
                        if os.path.isdir(f"{self.cfg2.ffdec_dir}_{name}") or os.path.isdir(f"{self.cfg2.ffdec_dir}_{name}_{i}"):
                            name=f"{name}_{i+1}"
                            break
                    shutil.move(self.cfg2.ffdec_dir, f"{self.cfg2.ffdec_dir}_{name}")
                except Exception as e:
                    print(f"Error occurred while updating old version: {e}")
        return self.download_ffdec()

    def upgrade(self):
        if self.cfg2.version < "1.7":
            print("Updating resources...")
            self.resource_update()
        self.cfg2.version = self.cfg2.default_config["version"]
        self.cfg2.save()
    
    def resource_update(self):
        if not os.path.isdir(self.docs_dir):
            return
        for name in os.listdir(self.docs_dir):
            subdir = os.path.join(self.docs_dir, name)
            index_path = os.path.join(subdir, "index.json")
            if os.path.isdir(subdir) and os.path.isfile(index_path):
                try:
                    with open(index_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    p_code = data["p_code"]
                    new_dir = os.path.join(self.docs_dir, p_code)
                    if not os.path.exists(new_dir):
                        os.makedirs(new_dir)
                    for file in os.listdir(subdir):
                        shutil.move(os.path.join(subdir, file), os.path.join(new_dir, file))
                    shutil.rmtree(subdir)
                except Exception as e:
                    print(f"Resource migrate failed: {subdir} -> {e}")
        self.gen_indexs()

    def gen_indexs(self):
        indexs = {}
        for name in os.listdir(self.docs_dir):
            subdir = os.path.join(self.docs_dir, name)
            index_path = os.path.join(subdir, "index.json")
            if os.path.isdir(subdir) and os.path.isfile(index_path):
                try:
                    with open(index_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    indexs[data["p_code"]] = data["p_name"]
                except Exception as e:
                    print(f"Index build failed: {subdir} -> {e}")
        with open(os.path.join(self.docs_dir, "indexs.json"), "w", encoding="utf-8") as f:
            json.dump(indexs, f, ensure_ascii=False, indent=2)

    def check_update(self):
        try:
            main_info = github_release("cmy2008/doc88_extractor")
            if main_info.latest_version.lstrip("V") > self.cfg2.default_config["version"]:
                print(f"New version: {main_info.latest_version}\n{main_info.download_url}")
            return True
        except Exception as e:
            print(f"Update check failed: {e}")
            return False
    
    def check_ffdec_update(self):
        try:
            rel, asset_name = self.get_ffdec_asset()
            display_name = asset_name if asset_name else rel.latest_version
            ffdec_jar = os.path.join(self.cfg2.ffdec_dir, "ffdec.jar")
            if rel.latest_version != self.cfg2.ffdec_version and os.path.isfile(ffdec_jar) and self.cfg2.check_update:
                if not choose(f"当前 ffdec 版本 {self.cfg2.ffdec_version}, 检测到新版本(文件名：{display_name})，是否更新？ (Y/n): "):
                    return False
            if rel.latest_version == self.cfg2.ffdec_version and os.path.isfile(ffdec_jar):
                return False
            if not self.ffdec_update() and not os.path.isfile(ffdec_jar):
                exit()
            self.cfg2.ffdec_version = rel.latest_version
            self.cfg2.save()
            return True
        except Exception as e:
            print(f"ffdec update check failed: {e}")
            if not os.path.isfile(os.path.join(self.cfg2.ffdec_dir, "ffdec.jar")):
                print("Manual install: https://github.com/jindrapetrik/jpexs-decompiler/releases")
                input_break()
                exit()
            return False
    
    def ffdec_configure(self):
        # 配置 ffdec 临时目录
        if cfg2.replace_jna_tmp_path:
            jna_dir = ospath(os.path.join(self.cfg2.ffdec_dir, "jna_temp"))
            if not os.path.exists(jna_dir):
                try:
                    os.makedirs(jna_dir)
                except FileNotFoundError:
                    print("ffdec temp folder create failed.")
            try:
                ffdec_jar = os.path.join(self.cfg2.ffdec_dir, "ffdec.jar")
                subprocess.run(
                    ["java", "-jar", ffdec_jar, "-config", f"jnaTempDirectory={os.path.abspath(jna_dir)}"],
                    capture_output=True,
                    text=True,
                    check=True
                )
            except Exception as err:
                logw(str(err))
                return False
        # 待 ffdec 修复
        '''
        else:
            try:
                subprocess.run(
                    ["java", "-jar", "ffdec/ffdec.jar", "-config", 'jnaTempDirectory=""'],
                    capture_output=True,
                    text=True
                )
            except Exception as err:
                logw(str(err))
        '''
        # 配置 font-face
        try:
            ffdec_jar = os.path.join(self.cfg2.ffdec_dir, "ffdec.jar")
            if cfg2.svgfontface:
                subprocess.run(
                    ["java", "-jar", ffdec_jar, "-config", "textExportExportFontFace=true"],
                    capture_output=True,
                    text=True,
                    check=True
                )
            else:
                subprocess.run(
                    ["java", "-jar", ffdec_jar, "-config", "textExportExportFontFace=false"],
                    capture_output=True,
                    text=True,
                    check=True
                )
        except Exception as err:
            logw(str(err))
            return False
        return True
    
    def download_svg2pdf(self):
        try:
            info = github_release(self.cfg2.svg2pdf_repo)
        except Exception as e:
            print(f"svg2pdf release check failed: {e}")
            return False
        dest_dir = os.path.dirname(self.cfg2.svg2pdf_path)
        os.makedirs(dest_dir, exist_ok=True)
        os_base_platform = platform.system()
        os_arch = platform.machine().lower()
        if os_base_platform == "Windows" and ("amd64" in os_arch or "x86_64" in os_arch):
            file_name = 'svg2pdf-x86_64-pc-windows-msvc.zip'
            svg2pdf_url = self.cfg2.proxy_url + info.releases[file_name]

        elif os_base_platform == "Darwin" and ("arm64" in os_arch or "aarch64" in os_arch):
            file_name = 'svg2pdf-aarch64-apple-darwin.tar.gz'
            svg2pdf_url = self.cfg2.proxy_url + info.releases[file_name]

        elif os_base_platform == "Darwin" and ("amd64" in os_arch or "x86_64" in os_arch):
            file_name = 'svg2pdf-x86_64-apple-darwin.tar.gz'
            svg2pdf_url = self.cfg2.proxy_url + info.releases[file_name]

        elif os_base_platform == "Linux" and ("amd64" in os_arch or "x86_64" in os_arch):
            file_name = 'svg2pdf-x86_64-unknown-linux-gnu.tar.gz'
            svg2pdf_url = self.cfg2.proxy_url + info.releases[file_name]

        # for Android support
        elif os_base_platform == "Linux" and ("arm64" in os_arch or "aarch64" in os_arch):
            uname = subprocess.run(['uname', '-o'], capture_output=True, text=True)
            if "Android" in uname.stdout or "Toybox" in uname.stdout or "BusyBox" in uname.stdout:
                file_name = 'svg2pdf-aarch64-android-libc.tar.gz'
            else:
                file_name = 'svg2pdf-aarch64-unknown-linux-gnu.tar.gz'
            svg2pdf_url = self.cfg2.proxy_url + info.releases[file_name]

        else:
            print("svg2pdf unsupported. Build from https://github.com/typst/svg2pdf")
            return False
        print("Downloading svg2pdf...")
        try:
            download(svg2pdf_url, os.path.join(dest_dir, file_name))
        except:
            print("Download failed. Check network or proxy_url.")
            input_break()
            return False
        print("Extracting svg2pdf...")
        try:
            archive = os.path.join(dest_dir, file_name)
            extract(archive, dest_dir)
            os.remove(archive)
            return True
        except zipfile.BadZipFile:
            print("Extract failed. Check svg2pdf_repo.")
            input_break()
            return False

    def check_svg2pdf(self):
        if self.cfg2.swf2svg:
            svg2pdf_bin = self.cfg2.svg2pdf_path + (".exe" if os.name == "nt" else "")
            if not os.path.isfile(svg2pdf_bin):
                if platform.system() == "Windows" or platform.system() == "Linux" or platform.system() == "Darwin":
                    if choose("检测到 svg2pdf 工具未下载，是否下载？ (Y/n): "):
                        return self.download_svg2pdf()
                    else:
                        print("svg2pdf not installed.")
                        return False
                else:
                    print("svg2pdf unsupported on this OS.")
                    return False
            else:
                return True