# -*- coding: utf-8 -*-

import os
import json
import re
import shutil
import subprocess
from .settings import *
from .swf_rebuild import *
from concurrent.futures import ThreadPoolExecutor
from pypdf import PdfWriter
from .metadata import *
from .page_scan import *
from .io_utils import *
from .updater import *

class get_cfg:
    def __init__(self, url: str) -> None:
        if "doc88.com/p-" not in url and "doc88.piglin.eu.org/p-" not in url:
            raise Exception("Invalid URL!")
        self.url = url
        self.content = ""
        self.data = ""
        self.sta = 0
        if not self.get_main() and choose("Do you want to use CDN?(Y/n): "):
            self.__init__("https://doc88.piglin.eu.org" + url[url.find("doc88.com/") + 9 :])

    def req(self):
        request = get_request(self.url)
        if request.status_code == 404:
            self.sta = 1
            raise Exception("404 Not found!")
        self.content = request.text

    def get_main(self):
        self.req()
        data = re.search(r"m_main.init\(\".*\"\);", self.content)
        if data is None:
            if re.search("网络环境安全验证", self.content):
                print("WAF detected")
                return False
            raise Exception("Config data not found! May be deleted?")
        c = data.span()
        self.data = self.content[c[0] + 13 : c[1] - 3]
        return True


def append_pdf(pdf: PdfWriter, file: str):
    pdf.append(ospath(file))
    return pdf
def init(config: dict) -> None:
    cfg2.dir_path = cfg2.o_dir_path + config["p_code"] + "/"
    cfg2.swf_path = cfg2.dir_path + cfg2.o_swf_path
    cfg2.svg_path = cfg2.dir_path + cfg2.o_svg_path
    cfg2.pdf_path = cfg2.dir_path + cfg2.o_pdf_path
    if os.path.exists(ospath(cfg2.dir_path)) and not choose("exists"):
        raise Exception("Canceled.")
    os.makedirs(ospath(cfg2.dir_path), exist_ok=True)
    if not os.path.exists(ospath(f"{cfg2.dir_path}index.json")):
        write_file(
            bytes(json.dumps(config), encoding="utf-8"),
            cfg2.dir_path + "index.json",
        )
    os.makedirs(ospath(cfg2.swf_path), exist_ok=True)
    os.makedirs(ospath(cfg2.svg_path), exist_ok=True)
    os.makedirs(ospath(cfg2.pdf_path), exist_ok=True)


def main(encoded_str, more=False):
    try:
        config = json.loads(decode(encoded_str))
    except json.decoder.JSONDecodeError:
        print("Invalid config data.")
        return False
    except (ValueError, UnicodeDecodeError):
        print("Invalid config data (key mismatch).")
        return False
    init(config)
    cfg = gen_cfg(config)
    if os.path.exists(ospath(f"{cfg2.dir_path}index.json")):
        cfg = gen_cfg(json.loads(read_file(f"{cfg2.dir_path}index.json")))
    print(f"Doc: {cfg.p_name} (ID {cfg.p_code}, pages {cfg.p_pagecount})")
    if int(cfg.p_pagecount) != cfg.p_count:
        more = True
        print(f"Preview pages: {cfg.p_countinfo}, direct pages: {cfg.p_count}")
    if not choose("开始提取？ (Y/n): "):
        return False
    if cfg.p_download == "1":
        if choose("down"):
            try:
                doc_format = str.lower(cfg.p_doc_format) if config["if_zip"] == 0 else "zip"
                os.makedirs(ospath(cfg2.o_out_path), exist_ok=True)
                file_path = os.path.join(cfg2.o_out_path, cfg.p_name + "." + doc_format)
                download(
                    get_request(
                        "https://www.doc88.com/doc.php?act=download&pcode=" + cfg.p_code
                    ).text,
                    file_path,
                )
                print("Saved: " + file_path)
                return True
            except Exception as err:
                print("Download error: " + str(err))
                logw("Download error: " + str(err))
    if more:
        if choose("即将通过扫描获取页面，是否继续（否则正常下载）？ (Y/n): "):
            print("Scanning extra pages...")
            newpageids = []
            cfg.p_count = 0
            for i in range(1, cfg.ph_nums() + 1):
                get = get_more(cfg, i, cfg2.dir_path, cfg.p_count)
                get.start()
                newpageids += get.newpageids
                cfg.p_count += len(get.newpageids)
                del get
            cfg.pageids = newpageids
            config["pageInfo"] = encode(",".join(newpageids))
            config["p_count"] = cfg.p_count
            write_file(
                bytes(json.dumps(config), encoding="utf-8"),
                cfg2.dir_path + "index.json",
            )
            print(f"Scanned pages: {cfg.p_count}")
            del newpageids
            time.sleep(2)
        else:
            more = False
    try:
        if not more:
            get_swf(cfg)
        convert(cfg)
        del cfg
        return True
    except Exception as err:
        print(err)
        return False


class downloader:
    def __init__(self, cfg: gen_cfg) -> None:
        self.cfg = cfg
        self.downloaded = True
        self.progressfile = cfg2.dir_path + "progress.json"
        if os.path.isfile(ospath(self.progressfile)):
            self.read_progress()
        else:
            self.progress = {"pk": [], "ph": []}

    def read_progress(self):
        try:
            self.progress = json.loads(read_file(self.progressfile))
        except json.decoder.JSONDecodeError:
            self.progress = {}

    def save_progress(self, type: str, page: int):
        self.progress[type].append(page)
        writes_file(json.dumps(self.progress), self.progressfile)

    def ph(self, i: int):
        url = self.cfg.ph(i)
        file_path = cfg2.dir_path + url.name
        if i in self.progress["ph"]:
            return None
        try:
            download(url.url, file_path)
            self.save_progress("ph", i)
        except Exception as e:
            logw(f"Download header {i} error: {e}")
            self.downloaded = False

    def pk(self, i: int):
        url = self.cfg.pk(i)
        file_path = cfg2.dir_path + url.name
        if i in self.progress["pk"]:
            return None
        try:
            download(url.url, file_path)
            self.save_progress("pk", i)
        except Exception as e:
            logw(f"Download page {i} error: {e}")
            self.downloaded = False

    def makeswf(self, i: int):
        try:
            level_num = self.cfg.ph_num(i)
            make_swf(
                cfg2.dir_path + self.cfg.ph(level_num).name,
                cfg2.dir_path + self.cfg.pk(i).name,
                cfg2.swf_path + str(i) + ".swf",
            )
        except Exception as e:
            print(f"Decompress failed: page {i}")
            logw(str(e))
            self.cfg.p_count -= 1


def get_swf(cfg: gen_cfg):
    max_workers = cfg2.download_workers
    down = downloader(cfg)
    print("Downloading headers...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for i in range(1, cfg.ph_nums() + 1):
            executor.submit(down.ph, i)
    print("Downloading pages...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for i in range(1, cfg.p_count + 1):
            executor.submit(down.pk, i)
    if not down.downloaded:
        raise Exception("Download error")
    print("Building SWF...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for i in range(1, cfg.p_count + 1):
            executor.submit(down.makeswf, i)
    print(f"Download done: {cfg.p_count} pages")

# TODO: 移除 cfg2 全局变量
class converter:
    def __init__(self) -> None:
        self.pdf = PdfWriter()
        self.pdflist = []

    # 帧画布大小修正
    def set_swf(self, i: int, w, h):
        ffdec_jar = os.path.join(cfg2.ffdec_dir, "ffdec.jar")
        return subprocess.run(
            ["java", "-jar", ffdec_jar, "-header", "-set", "width", f"{w}px", "-set", "height", f"{h}px", f"{cfg2.swf_path}{i}.swf", f"{cfg2.swf_path}{i}.swf"],
                capture_output=True,
                text=True,
            )

    def swf2svg(self, i: int):
        if os.listdir(ospath(f"{cfg2.swf_path}{i}")) == []:
            return
        log = ""
        try:
            dirpath = cfg2.svg_path + str(i) + "/"
            ffdec_jar = os.path.join(cfg2.ffdec_dir, "ffdec.jar")
            run = subprocess.run(
                ["java", "-jar", ffdec_jar, "-format", "frame:svg", "-select", "1", "-export", "frame", dirpath, f"{cfg2.swf_path}{i}"],
                capture_output=True,
                text=True,
            )
            log = run.stdout
            if run.returncode != 0:
                logw("SVG converting error: " + (run.stderr or run.stdout))
            for f in os.listdir(ospath(dirpath)):
                if os.path.isdir(ospath(f"{dirpath}{f}")):
                    shutil.move(
                        ospath(f"{dirpath}{f}/1.svg"), ospath(f"{cfg2.svg_path}{f[:-4]}.svg")
                    )
            # 删除ffdec的临时文件夹
            try:
                shutil.rmtree(ospath(f"{dirpath}"))
            except PermissionError:
                print("Can't delete temporary folder, maybe file is opened?")
            # 删除分组文件夹
            try:
                shutil.rmtree(ospath(f"{cfg2.swf_path}{i}/"))
            except PermissionError:
                print("Can't delete temporary folder, maybe file is opened?")
            except FileNotFoundError:
                pass
        except FileNotFoundError:
            logw("SVG converting error: " + log)

    def swf2pdf(self, i: int):
        if os.listdir(ospath(f"{cfg2.swf_path}{i}")) == []:
            return
        log = ""
        try:
            dirpath = cfg2.pdf_path + str(i) + "/"
            ffdec_jar = os.path.join(cfg2.ffdec_dir, "ffdec.jar")
            run = subprocess.run(
                ["java", "-jar", ffdec_jar, "-format", "frame:pdf", "-zoom", str(cfg2.pdf_scale), "-select", "1", "-export", "frame", dirpath, f"{cfg2.swf_path}{i}"],
                capture_output=True,
                text=True,
            )
            log = run.stdout
            if run.returncode != 0:
                logw("PDF converting error: " + (run.stderr or run.stdout))
            for f in os.listdir(ospath(dirpath)):
                if os.path.isdir(ospath(f"{dirpath}{f}")):
                    shutil.move(
                        ospath(f"{dirpath}{f}/frames.pdf"), ospath(f"{cfg2.pdf_path}{f[:-4]}.pdf")
                    )
                    self.pdflist.append(f[:-4])
            # 删除ffdec的临时文件夹
            try:
                shutil.rmtree(ospath(f"{dirpath}"))
            except PermissionError:
                print("Can't delete temporary folder, maybe file is opened?")
            # 删除分组文件夹
            try:
                shutil.rmtree(ospath(f"{cfg2.swf_path}{i}/"))
            except PermissionError:
                print("Can't delete temporary folder, maybe file is opened?")
            except FileNotFoundError:
                pass
        except FileNotFoundError:
            logw("PDF converting error: " + log)

    def svg2pdf(self, i: int):
        try:
            # cairosvg.svg2pdf(
            #     url=f"{cfg2.pdf_path}{i}_.svg",
            #     write_to=str(ospath(f"{cfg2.pdf_path}{i}.pdf")),
            # )
            svg2pdf_bin = cfg2.svg2pdf_path + (".exe" if os.name == "nt" else "")
            run=subprocess.run(
                [svg2pdf_bin, f"{cfg2.svg_path}{i}.svg", f"{cfg2.pdf_path}{i}.pdf"], text=True, capture_output=True
            )
            self.pdflist.append(i)
        except FileNotFoundError as e:
            logw(f"SVG to PDF converting error: {e}")

    def makepdf(self):
        self.pdflist = sorted(self.pdflist, key=lambda x: int(x))
        for i in self.pdflist:
            self.pdf = append_pdf(
                self.pdf, str(ospath(f"{cfg2.pdf_path}{i}.pdf"))
            )
    # 根据工作流数量平均分配 SWF 文件到各组文件夹中
    def divide_swfs(self, count: int):
        file_index = os.listdir(ospath(cfg2.swf_path))
        swf_files = sorted([f for f in file_index if f.endswith('.swf')], key=lambda x: int(x[:-4]))
        for idx, swf_file in enumerate(swf_files):
            group_num = idx % count
            group_path = ospath(f"{cfg2.swf_path}{group_num}/")
            try:
                os.makedirs(group_path)
            except FileExistsError:
                pass
            src_path = os.path.join(ospath(cfg2.swf_path), swf_file)
            dest_path = os.path.join(group_path, swf_file)
            shutil.copy(src_path, dest_path)


def convert(cfg: gen_cfg):
    print("Converting...")
    max_workers = cfg2.convert_workers
    doc = converter()
    if cfg2.fix_displayrect:
        print("Fixing displayrect...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for i in range(1, cfg.p_count + 1):
                executor.submit(doc.set_swf, i, cfg.pageids[i-1].split("-")[1], cfg.pageids[i-1].split("-")[2])
    doc.divide_swfs(cfg2.convert_workers)
    if not cfg2.swf2svg:
        print("SWF -> PDF")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for i in range(0, max_workers):
                executor.submit(doc.swf2pdf, i)
    else:
        print("SWF -> SVG")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for i in range(0, max_workers):
                executor.submit(doc.swf2svg, i)
        print("SVG -> PDF")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for i in range(1, cfg.p_count + 1):
                executor.submit(doc.svg2pdf, i)
    print("Merging PDF...")
    doc.makepdf()
    os.makedirs(ospath(cfg2.o_out_path), exist_ok=True)
    pdf_name = os.path.join(cfg2.o_out_path, special_path(cfg.p_name) + ".pdf")
    doc.pdf.write(str(ospath(pdf_name)))
    print("Saved: " + pdf_name)


def clean(cfg2):
    print("Cleaning cache...")
    shutil.rmtree(ospath(cfg2.swf_path), ignore_errors=True)
    shutil.rmtree(ospath(cfg2.pdf_path), ignore_errors=True)
    shutil.rmtree(ospath(cfg2.svg_path), ignore_errors=True)
    shutil.rmtree(ospath(cfg2.dir_path), ignore_errors=True)


def run(url: str | None = None) -> bool:
    update = Update(cfg2)
    if not update.check_java():
        input_break()
        return False
    update.check_ffdec_update()
    if cfg2.check_update:
        update.check_update()
    update.upgrade()
    if not update.ffdec_configure():
        print("ffdec configure failed. Check Java and ffdec install.")
        input_break()
        return False
    if cfg2.swf2svg and not update.check_svg2pdf():
        print("svg2pdf unavailable; fallback to SWF -> PDF")
        cfg2.swf2svg = False

    if url is None:
        try:
            url = input("请输入网址：")
        except KeyboardInterrupt:
            return False
    try:
        ok = main(get_cfg(url).data, cfg2.get_more)
    except Exception as err:
        print(err)
        ok = False
    if ok and cfg2.clean:
        clean(cfg2)
    return ok
