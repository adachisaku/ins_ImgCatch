import time
import requests
import re
import os
import tkinter as tk
from tkinter import messagebox, filedialog, scrolledtext
import io
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

global progress
progress = 1
seen_images = set()
tnl = ""
lock = threading.Lock()

class PrintLogger(io.StringIO):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def write(self, s):
        super().write(s)
        self.callback(s)

def make_response(username, ec, page_no=1, images_count=0, base_folder_name="",
                  download_all_in_one_folder=True):
    global tnl #记录上一张图片的url
    url = "https://www.instagram.com/graphql/query"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }
    variables_str = "{{\"after\":\"{ec}\",\"before\":null,\"data\":{{\"count\":12,\"include_relationship_info\":true,\"latest_besties_reel_media\":true,\"latest_reel_media\":true}},\"first\":12,\"last\":null,\"username\":\"{username}\",\"__relay_internal__pv__PolarisShareMenurelayprovider\":false}}".format(
        ec=ec, username=username)
    data = {
        "av": "17841466101064805",
        "__d": "www",
        "__user": "0",
        "__a": "1",
        "__req": "5",
        "__hs": "19891.HYP:instagram_web_pkg.2.1..0.1",
        "dpr": "1",
        "__ccg": "UNKNOWN",
        "__rev": "1014264940",
        "__s": "1p26gv:a50m9o:uj3yvr",
        "__hsi": "7381386167097344375",
        "__dyn": "7xe5WwlEnwn8K2Wmm0NonwgU7S6EdF8aUco38w5ux609vCwjE1xoswaq0yE6u0nS4oaEd86a3a1YwBgao1aU2swbOU2zxe2GewGw9a362W2K0zEnwhEe82mw4JwJCwLyES1Twoob82ZwrUdUbGwmk0KU6O1FwlE6PhA6bwQyUrAwHyokxK3OqcxK2K",
        "__csr": "gx9kfMN4tYAj5hicOiqNqq9uPhlkOy4X-zAABQhfI-lqWiK8yfmHiUXCleF9UCXSGXjRDkKAKWAG9hV4_BQbApoHmicxpohgOKh5jBijye4FWCxnKHKpGh5HzGz8NAxq8VHybKcy8mCLDgaoOm00lSe2C0EPw5US6V40IoKU0h0w1Igyswc86cjeAlQl0zghwOwDg4Cifw6QPw5Twv80LsODw5sDwVwle0bAg3hDw098K",
        "__comet_req": "7",
        "variables": variables_str,
        "server_timestamps": "true",
        "doc_id": "7648235718586670",
    }

    response = requests.post(url, headers=headers, data=data)
    match1 = re.search(r'"end_cursor":"(\d+_\d+)"', response.text)

    if match1:
        ex_response = response.text.replace('\\u0026', '&')
        matches = re.findall(r'\{"url":"([^"]+)","height":1800,"width":1440}', ex_response) #筛选最大尺寸图片

        if download_all_in_one_folder:
            folder_name = base_folder_name
        else:
            folder_name = os.path.join(base_folder_name, f"Page_{page_no}")
            os.makedirs(folder_name, exist_ok=True)

        images_count += len(matches)

        with ThreadPoolExecutor(max_workers=5) as executor:  # max_workers 根据需要调整
            futures = []
            for index, img_url in enumerate(matches):
                if progress == 0:
                    while progress == 0:
                        time.sleep(0.1)
                futures.append(executor.submit(download_image, img_url, folder_name, index, images_count, matches))

            for future in as_completed(futures):
                pass

        new_ec = match1.group(1)
        time.sleep(3)
        make_response(username, new_ec, page_no + 1, images_count, base_folder_name, download_all_in_one_folder)
    else:
        print(f"获取完成。总计页面数: {page_no}, 总计图片数: {images_count}.")


def download_image(img_url, folder_name, img_index, images_count, matches):
    """下载单个图片并保存"""
    global tnl  # 记录上一张图片的url
    try:
        img_num = re.search(r'/(\d+_\d+_\d+)_n', img_url)
        if img_num:
            with lock:
                current_tnl = img_num.group(1)
                if current_tnl == tnl:
                    return  # 如果当前图片与上一张重复则跳过
                else:
                    tnl = current_tnl

        while progress == 0:
            time.sleep(0.1)

        response = requests.get(img_url, timeout=10)
        response.raise_for_status()  # 检查请求是否成功
        img_data = response.content

        with lock:
            seen_images.add(img_url)

        img_path = os.path.join(folder_name, f"image_{images_count - len(matches) + img_index + 1}.jpg")
        with open(img_path, 'wb') as img_file:
            img_file.write(img_data)
        print(f"保存至 {img_path}")
    except Exception as e:
        print(f"保存失败 {img_url}:\n {e}")

def start_download(username, base_folder_name, download_all_in_one_folder):
    global progress
    progress = 1
    make_response(username, "", 1, 0, base_folder_name, download_all_in_one_folder)

def toggle_pause_resume(progress_callback):  #控制暂停和继续下载
    global progress
    if progress == 1:
        progress = 0
        pause_resume_button.config(text="继续下载")
        progress_callback("已暂停下载.\n")
    else:
        progress = 1
        pause_resume_button.config(text="暂停下载")
        progress_callback("已继续下载.\n")

def stop_download():
    global progress
    progress = 0
    print("下载已停止.")

def create_gui():
    def on_start():
        username = username_entry.get().strip()
        base_folder_name = path_entry.get().strip()
        if username and base_folder_name:
            text_area.delete(1.0, tk.END)
            download_all_in_one_folder = download_mode.get() == 2
            threading.Thread(target=start_download, args=(username, base_folder_name, download_all_in_one_folder)).start()
        else:
            messagebox.showwarning("警告", "请输入正确的名字或路径")

    def on_stop():
        stop_download()
        text_area.insert(tk.END, "下载已停止.\n")

    def on_close():
        if messagebox.askokcancel("确认", "确定要退出程序吗？"):
            stop_download()
            window.quit()
            window.destroy()
            os._exit(0)  # 强制终止所有线程

    def select_path():
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            path_entry.delete(0, tk.END)
            path_entry.insert(0, folder_selected)

    window = tk.Tk()
    window.title("Ins博主照片下载器")

    main_frame = tk.Frame(window, padx=10, pady=10)
    main_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    username_frame = tk.Frame(main_frame)
    username_frame.pack(fill=tk.X, pady=5)
    tk.Label(username_frame, text="输入博主名字：").pack(side=tk.LEFT, padx=5)
    global username_entry
    username_entry = tk.Entry(username_frame, width=50)
    username_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

    path_frame = tk.Frame(main_frame)
    path_frame.pack(fill=tk.X, pady=5)
    tk.Label(path_frame, text="下载路径：").pack(side=tk.LEFT, padx=5)
    global path_entry
    path_entry = tk.Entry(path_frame, width=40)
    path_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
    path_button = tk.Button(path_frame, text="浏览", command=select_path)
    path_button.pack(side=tk.LEFT, padx=5)

    mode_frame = tk.Frame(main_frame)
    mode_frame.pack(fill=tk.X, pady=5)
    global download_mode
    download_mode = tk.IntVar(value=1)
    tk.Radiobutton(mode_frame, text="分文件夹下载", variable=download_mode, value=1).pack(side=tk.LEFT, padx=5)
    tk.Radiobutton(mode_frame, text="单个文件夹下载", variable=download_mode, value=2).pack(side=tk.LEFT, padx=5)

    button_frame = tk.Frame(main_frame)
    button_frame.pack(pady=5)
    start_button = tk.Button(button_frame, text="开始下载", command=on_start)
    start_button.pack(side=tk.LEFT, padx=5)
    global pause_resume_button
    pause_resume_button = tk.Button(button_frame, text="暂停下载",
                                    command=lambda: toggle_pause_resume(lambda msg: text_area.insert(tk.END, msg)))
    pause_resume_button.pack(side=tk.LEFT, padx=5)
    stop_button = tk.Button(button_frame, text="停止下载", command=on_stop)
    stop_button.pack(side=tk.LEFT, padx=5)

    text_area_frame = tk.Frame(main_frame)
    text_area_frame.pack(fill=tk.BOTH, expand=True)
    text_area_label = tk.Label(text_area_frame, text="下载日志：")
    text_area_label.pack(anchor=tk.W)
    global text_area
    text_area = scrolledtext.ScrolledText(text_area_frame, wrap=tk.WORD, height=20)
    text_area.pack(fill=tk.BOTH, expand=True)

    sys.stdout = PrintLogger(lambda msg: text_area.insert(tk.END, msg))
    sys.stderr = PrintLogger(lambda msg: text_area.insert(tk.END, msg))

    window.protocol("WM_DELETE_WINDOW", on_close)
    window.mainloop()

if __name__ == "__main__":
    create_gui()