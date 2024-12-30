#!/usr/bin/env python
# coding: utf-8

# 项目资源管理器，项目视图的元素之一。
# 包含：标题图，项目管理按钮，媒体、角色、剧本的可折叠容器

import os
import sys
import json
import re
import glob
from PIL import Image, ImageTk, ImageEnhance, ImageFont, ImageDraw
import ttkbootstrap as ttk
import tkinter as tk
from ttkbootstrap.dialogs import Messagebox
from ttkbootstrap.tooltip import ToolTip
from ttkbootstrap.toast import ToastNotification
from .ScriptParser import MediaDef, CharTable, RplGenLog, Script
from .FilePaths import Filepath
from .ProjConfig import Config, preference
from .Exceptions import MediaError
from .Medias import MediaObj
from .Boardcast import BoardcastHandler
from .GUI_TabPage import PageFrame, RGLPage, CTBPage, MDFPage
from .GUI_DialogWindow import browse_file, save_file, browse_multi_file
from .GUI_CustomDialog import relocate_file, configure_project, select_template
from .GUI_Util import FluentFrame, ask_rename_boardcast
from .GUI_Language import tr
from .GUI_Link import Link
import pinyin
from .Utils import readable_timestamp
import shutil

# 项目视图-文件管理器-RGPJ
class RplGenProJect(Script):
    def __init__(self, json_input=None) -> None:
        # 新建空白工程
        if json_input is None:
            self.config     = Config()
            self.mediadef   = MediaDef(file_input='./toy/MediaObject.txt')
            # 设置当前路径
            Filepath.Mediapath = './toy/' #self.media_path
            self.chartab    = CharTable(file_input='./toy/CharactorTable.tsv')
            self.logfile    = {
                '示例项目1' : RplGenLog(file_input='./toy/LogFile.rgl'),
                '示例项目2' : RplGenLog(file_input='./toy/LogFile2.rgl')
                }
        # 载入json工程文件
        else:
            super().__init__(None, None, None, json_input)
            # config
            self.config     = Config(dict_input=self.struct['config'])
            # media
            Filepath.Mediapath = Filepath(json_input).directory()
            self.mediadef   = MediaDef(dict_input=self.struct['mediadef'])
            # chartab
            self.chartab    = CharTable(dict_input=self.struct['chartab'])
            # logfile
            self.logfile    = {}
            for key in self.struct['logfile'].keys():
                self.logfile[key] = RplGenLog(dict_input=self.struct['logfile'][key])
        # 广播
        self.boardcast = BoardcastHandler(
            mediadef=self.mediadef,
            chartab=self.chartab,
            logfile=self.logfile
        )
        # 保存在全局连接
        Link['boardcast'] = self.boardcast
        Link['project_chartab'] = self.chartab
        Link['project_config'] = self.config
        Link['media_dir'] = Filepath.Mediapath
    def dump_json(self, filepath: str) -> None:
        logfile_dict = {}
        for key in self.logfile.keys():
            logfile_dict[key] = self.logfile[key].struct
        with open(filepath,'w',encoding='utf-8') as of:
            of.write(
                json.dumps(
                    {
                        'config'  : self.config.get_struct(),
                        'mediadef': self.mediadef.struct,
                        'chartab' : self.chartab.struct,
                        'logfile' : logfile_dict,
                    }
                    ,indent=4
                )
            )

# 项目视图-文件管理器
class FileManager(ttk.Frame):
    def __init__(self, master, screenzoom, page_frame:PageFrame, project_file:str=None)->None:
        self.sz = screenzoom
        super().__init__(master,borderwidth=0)
        self.master = master
        # 文件管理器的项目对象
        self.project:RplGenProJect = RplGenProJect(json_input=project_file)
        self.project_file:str = project_file
        # 图形
        SZ_30 = int(self.sz * 30)
        icon_size = [SZ_30,SZ_30]
        self.image = {
            'save'      : ImageTk.PhotoImage(name='save' ,   image=Image.open('./assets/icon/save.png').resize(icon_size)),
            'config'    : ImageTk.PhotoImage(name='config',   image=Image.open('./assets/icon/setting.png').resize(icon_size)),
            'template'  : ImageTk.PhotoImage(name='template', image=Image.open('./assets/icon/template.png').resize(icon_size)),
            'import'    : ImageTk.PhotoImage(name='import',   image=Image.open('./assets/icon/import.png').resize(icon_size)),
            'export'    : ImageTk.PhotoImage(name='export',   image=Image.open('./assets/icon/export.png').resize(icon_size)),
            'close'     : ImageTk.PhotoImage(name='close',   image=Image.open('./assets/icon/close.png').resize(icon_size)),
        }
        # 标题
        self.project_title = ttk.Frame(master=self,borderwidth=0,bootstyle='light')
        # 保存一次
        self.write_recent_project(name=self.project.config.Name, path=self.project_file)
        # 封面图
        self.title_pic = ttk.Label(master=self.project_title,borderwidth=0)
        self.load_cover()
        # 按钮
        SZ_5 = int(self.sz * 5)
        button_padding = [0,SZ_5,0,SZ_5]
        self.buttons = {
            'save'      : ttk.Button(master=self.project_title,image='save'  ,command=self.save_file, cursor='hand2',padding=button_padding),
            'config'    : ttk.Button(master=self.project_title,image='config',command=self.proj_config, cursor='hand2',padding=button_padding),
            'template'  : ttk.Button(master=self.project_title,image='template',command=self.import_template, cursor='hand2',padding=button_padding),
            'import'    : ttk.Button(master=self.project_title,image='import',command=self.import_file, cursor='hand2',padding=button_padding),
            'export'    : ttk.Button(master=self.project_title,image='export',command=self.export_file, cursor='hand2',padding=button_padding),
            'close'     : ttk.Button(master=self.project_title,image='close',command=self.close_proj, cursor='hand2',padding=button_padding),
        }
        self.buttons_tooltip = {
            'save'      : ToolTip(widget=self.buttons['save']  ,text=tr('保存项目'),bootstyle='secondary-inverse'),
            'config'    : ToolTip(widget=self.buttons['config'],text=tr('项目设置'),bootstyle='secondary-inverse'),
            'template'  : ToolTip(widget=self.buttons['template'],text=tr('导入模板素材'),bootstyle='secondary-inverse'),
            'import'    : ToolTip(widget=self.buttons['import'],text=tr('导入工程文件'),bootstyle='secondary-inverse'),
            'export'    : ToolTip(widget=self.buttons['export'],text=tr('导出工程文件'),bootstyle='secondary-inverse'),
            'close'     : ToolTip(widget=self.buttons['close'], text=tr('关闭项目'),bootstyle='danger-inverse'),
        }
        # 放置
        self.title_pic.pack(fill='none',side='top')
        for idx,key in enumerate(self.buttons):
            buttons:ttk.Button = self.buttons[key]
            buttons.pack(expand=True,fill='x',side='left',anchor='se',padx=0,pady=0)
        self.project_title.pack(fill='x',side='top',padx=0,pady=0,ipadx=0,ipady=0)
        # 在初始化的时候，检查文件可用性
        self.check_project_media_exist()
        # 文件浏览器元件
        self.project_content = FluentFrame(master=self,borderwidth=0,bootstyle='light',autohide=True)
        self.project_content.vscroll.config(bootstyle='secondary-round')
        # 对应的page_frame对象
        self.page_frame:PageFrame = page_frame
        self.page_frame.ref_medef = self.project.mediadef
        self.page_frame.ref_chartab = self.project.chartab
        self.page_frame.ref_config = self.project.config
        # 元件
        self.items = {
            'mediadef'  : MDFCollapsing(master=self.project_content,screenzoom=self.sz,content=self.project.mediadef,page_frame=self.page_frame),
            'chartab'   : CTBCollapsing(master=self.project_content,screenzoom=self.sz,content=self.project.chartab,page_frame=self.page_frame),
            'rplgenlog' : RGLCollapsing(master=self.project_content,screenzoom=self.sz,content=self.project.logfile,page_frame=self.page_frame),
        }
        # 放置
        self.update_item()
    def update_item(self):
        SZ_10 = int(self.sz*10)
        SZ_2 = int(self.sz * 2)
        for idx,key in enumerate(self.items):
            fileitem:FileCollapsing = self.items[key]
            fileitem.pack(fill='x',pady=(0,SZ_2),padx=0,side='top')
        self.project_content.pack(fill='both',expand=True,side='top')
    # 检查相关文件是否存在
    def check_file_exist(self,filepath:str)->bool:
        if filepath in MediaObj.cmap.keys() or filepath == 'None' or filepath is None:
            return True
        try:
            Filepath(filepath).exact()
            return True
        except MediaError:
            return False
    # 项目层面上的整体文件检查，如果存在脱机素材会唤起定位文件的对话框
    def check_project_media_exist(self):
        file_not_found = {}
        for keyword in self.project.mediadef.struct:
            this_section:dict = self.project.mediadef.struct[keyword]
            # 检查文件可用性
            if 'filepath' in this_section:
                file_path = this_section['filepath']
            elif 'fontfile' in this_section:
                file_path = this_section['fontfile']
            else:
                file_path = None
            if not self.check_file_exist(file_path):
                file_not_found[keyword] = file_path
        # 检查是否有脱机素材，如果有则启动重定位
        if len(file_not_found) != 0:
            # 这个步骤可能会改变mediadef！
            relocate_file(master=self,file_not_found=file_not_found,mediadef=self.project.mediadef)
    # 解析文件
    def parse_file(self,filepath)->tuple:
        # 尝试多个解析
        Types = {'mediadef':None,'chartab':None,'rplgenlog':None}
        for t in Types:
            ScriptType = {'mediadef':MediaDef,'chartab':CharTable,'rplgenlog':RplGenLog}[t]
            try:
                this = ScriptType(file_input=filepath)
                Types[t] = this
            except:
                Types[t] = ScriptType()
        # 获取最优解析结果
        top_parse:str = max(Types,key=lambda x:len(Types.get(x).struct))
        top_results = Types[top_parse]
        return (top_parse, len(top_results.struct), top_results) # 类型、长度、对象
    # 载入文件
    def load_file(self,path,ftype,object):
        count_of_add = 0
        count_of_rep = 0
        if ftype == 'mediadef':
            imported:MediaDef = object
            collapse:MDFCollapsing = self.items['mediadef']
            for keyword in imported.struct:
                # 检查是否是无效行
                if imported.struct[keyword]['type'] in ['comment','blank']:
                    continue
                # 检查文件名是否重复
                keyword_new = keyword
                if preference.import_mode == 'add':
                    while keyword_new in self.project.mediadef.struct.keys():
                        keyword_new = keyword_new + '_new'
                    else:
                        count_of_add += 1
                else:
                    if keyword_new in self.project.mediadef.struct.keys():
                        count_of_rep += 1
                    else:
                        count_of_add += 1
                # 执行变更
                self.project.mediadef.struct[keyword_new] = imported.struct[keyword]
            # 返回summary
            if count_of_rep == 0:
                return tr("向媒体库中导入媒体对象{ct}个。").format(ct=count_of_add)
            else:
                return tr("向媒体库中导入媒体对象{ct}个；更新媒体对象{cr}个。").format(ct=count_of_add,cr=count_of_rep)
        elif ftype == 'chartab':
            imported:CharTable = object
            collapse:CTBCollapsing = self.items['chartab']
            new_charactor:list = []
            # 检查，是否存在额外的自定义列，有则新建自定义列
            for col in imported.customize_col:
                if col not in self.project.chartab.customize_col:
                    self.project.chartab.add_customize(colname=col)
            # 检查，是否存在重名对象
            for keyword in imported.struct:
                name, subtype = keyword.split('.')
                # 是不是一个新增的角色？是则新建标签
                if name not in collapse.get_chara_name():
                    new_charactor.append(name)
                    collapse.create_new_button(new_keyword=name)
                # 如果重名了
                keyword_new = keyword
                if preference.import_mode == 'add':
                    while keyword_new in self.project.chartab.struct.keys():
                        keyword_new = keyword_new + '_new'
                        subtype = subtype + '_new'
                    else:
                        # 更新项目内容
                        imported.struct[keyword]['Subtype'] = subtype
                        count_of_add += 1
                else:
                    # 如果是覆盖模式，则什么都不做
                    if keyword_new in self.project.chartab.struct.keys():
                        count_of_rep += 1
                    else:
                        count_of_add += 1
                # 应用变更
                self.project.chartab.struct[keyword_new] = imported.struct[keyword]
            # 最后，检查所有新建角色，有没有default，没有则新建
            for chara in new_charactor:
                self.project.chartab.add_chara_default(name=chara)
                count_of_add += 1
            # 返回summary
            if count_of_rep == 0:
                return tr("向角色配置中导入新角色{nc}个；新增角色差分{ct}个。").format(nc=len(new_charactor),ct=count_of_add)
            else:
                return tr("向角色配置中导入新角色{nc}个；新增角色差分{ct}个，更新角色差分{cr}个。").format(nc=len(new_charactor),ct=count_of_add,cr=count_of_rep)
        else: # rplgenlog
            imported:RplGenLog = object
            collapse:RGLCollapsing = self.items['rplgenlog']
            filename = Filepath(path).prefix()
            # 如果重名了，在名字后面加东西
            while filename in self.project.logfile.keys():
                filename = filename+'_new'
            else:
                # 更新项目内容
                self.project.logfile[filename] = imported
                count_of_add = len(imported.struct)
                # 更新文件管理器
                collapse.create_new_button(new_keyword=filename)
            # import_mode 对rgl不生效
            return tr("向剧本文件中添加新剧本【{fn}】，包含{ct}个小节。").format(fn=filename,ct=count_of_add)
    # 导入模板
    def import_template(self):
        # 选择模板，并导入
        imported:dict = select_template(
            master=self,
            project_path=self.project_file
            )
        count_of_add = 0
        count_of_rep = 0
        # 将导入的媒体对象添加到项目
        if imported:
            for keyword in imported:
                # 检查文件名是否重复
                keyword_new = keyword
                if preference.import_mode == 'add':
                    while keyword_new in self.project.mediadef.struct.keys():
                        keyword_new = keyword_new + '_new'
                    else:
                        count_of_add += 1
                else:
                    if keyword_new in self.project.mediadef.struct.keys():
                        count_of_rep += 1
                    else:
                        count_of_add += 1
                # 执行变更
                self.project.mediadef.struct[keyword_new] = imported[keyword]
            # summary
            if count_of_rep == 0:
                message = tr("向媒体库中导入媒体对象{ct}个。").format(ct=count_of_add)
            else:
                message = tr("向媒体库中导入媒体对象{ct}个；更新媒体对象{cr}个。").format(ct=count_of_add,cr=count_of_rep)

            # 检查是否有脱机素材，如果有则启动重定位
            self.check_project_media_exist()
            # 刷新已有标签页的page_element
            self.update_pages_elements(ftype='medef')
            # 显示
            Messagebox().show_info(
                title   = tr('导入文件'),
                message = message,
                parent  = self
                )
        else:
            pass
    # 导入文件
    def import_file(self):
        get_file:list = browse_multi_file(master=self.winfo_toplevel(),filetype='rgscripts',related=False)
        if get_file:
            # 尝试多个解析
            summary_recode = {}
            type_recode = []
            # 是否是更新项目模式？
            self.is_update_project:bool = None
            # 开始遍历
            for file in get_file:
                Tp,Lt,Ob = self.parse_file(file)
                # 记录
                if Lt != 0:
                    summary_recode[file] = self.load_file(path=file, ftype=Tp, object=Ob)
                    type_recode.append(Tp)
                else:
                    summary_recode[file] = tr('导入失败，无法读取该文件！')
            # 是否需要刷新视图
            if 'mediadef' in type_recode:
                # 检查是否有脱机素材，如果有则启动重定位
                self.check_project_media_exist()
                # 刷新已有标签页的page_element
                self.update_pages_elements(ftype='medef')
            elif 'chartab' in type_recode:
                # 刷新已有标签页的page_element
                self.update_pages_elements(ftype='chartab')
            # 最后总结
            summary = tr('导入如下文件：\n')
            for file in summary_recode:
                text = summary_recode[file]
                filename = file.replace('\\','/').split('/')[-1]
                summary = summary + f"{filename}：{text}\n"
            Messagebox().show_info(
                title   = tr('导入文件'),
                message = summary[:-1],
                parent  = self
                )
    # 导出文件
    def export_file(self):
        # 如果导出完整的项目为脚本
        get_file = save_file(master=self.winfo_toplevel(), method='file',filetype='prefix')
        if get_file != '':
            try:
                # 媒体定义
                self.project.mediadef.dump_file(filepath=get_file+'.'+tr('媒体库')+'.txt')
                # 角色配置
                self.project.chartab.dump_file(filepath=get_file+'.'+tr('角色配置')+'.tsv')
                # 剧本文件
                for keyword, rgl in self.project.logfile.items():
                    rgl.dump_file(filepath=get_file+'.{}.rgl'.format(keyword))
                # 显示消息
                Messagebox().show_info(title=tr('导出成功'),message=tr('成功将工程导出为脚本文件！\n导出路径：{}').format(get_file),parent=self)
            except Exception as E:
                Messagebox().show_error(title=tr('导出失败'),message=tr('无法将工程导出！\n由于：{}').format(E),parent=self)
    # 保存文件
    def save_file(self):
        # 先去尝试将目前启动的所有rgl窗口保存了
        page_dict:dict = self.master.page_frame.page_dict
        warning_message = {}
        for page in page_dict:
            if page[0:2] == '剧本' or page[0:3] == 'RGL':
                try:
                    page_dict[page].update_rplgenlog()
                except Exception as E:
                    warning_message[page] = re.sub('\x1B\[\d+m','',str(E))
        if len(warning_message) != 0:
            message = '\n'.join([tr("保存【{p}】时出现异常：{w}").format(p=page,w=warning_message[page]) for page in warning_message])
            Messagebox().show_warning(message=message+tr('\n在异常得到解决前，上述剧本文件的变更将无法得到保存！'),title=tr('警告'),parent=self)
        # 将整个项目dump下来
        if self.project_file is None:
            select_path = save_file(master=self.winfo_toplevel(),filetype='rplgenproj')
            if select_path != '':
                self.project.dump_json(filepath=select_path)
                self.project_file = select_path
        else:
            # 先把旧的项目文件输出到backup
            self.backup_file()
            # 然后将新的项目覆写到原有的项目
            self.project.dump_json(filepath=self.project_file)
        # 弹出消息提示，Toast
        ToastNotification(
            title=tr('保存成功'),
            message=tr('成功保存项目到文件：\n')+self.project_file,
            duration=3000
        ).show_toast()
    # 备份项目
    def backup_file(self):
        # 输出路径
        output_path = Link['media_dir'] + f'backup/'
        # 备份的路径
        backup_file = f"{output_path}{self.project.config.Name}.{readable_timestamp()}.rgpj"
        # 检查输出路径是否存在
        if not os.path.isdir(output_path):
            os.makedirs(output_path)
        # 执行复制
        try:
            shutil.copy(src=self.project_file, dst=backup_file)
        except OSError:
            # TODO: 由于项目文件名包含非法字符的原因，可能会导致无法正常备份，在这里处理这种异常
            pass
        # 检查备份文件夹的存档数量，保证数量不超过10
        list_of_backup = glob.glob(f"{output_path}{self.project.config.Name}.*.rgpj")
        list_of_backup.sort() # 升序排序
        while len(list_of_backup) > 10:
            # 删除列表开头的文件（即创建时间最小的）
            os.remove(list_of_backup.pop(0))
    # 配置项目
    def proj_config(self):
        get_config = configure_project(
            master=self,
            proj_config=self.project.config.get_struct(),
            file_path = self.project_file
            )
        if get_config:
            # 载入值
            self.project.config.set_struct(dict_input=get_config)
            # 执行config
            self.project.config.execute()
            # 更换标题图
            self.load_cover()
    # 关闭项目
    def close_proj(self):
        toplevel = self.winfo_toplevel()
        w = int(toplevel.winfo_width()/2)
        h = int(toplevel.winfo_height()/2-self.sz*100)
        x = int(self.winfo_x())
        y = int(self.winfo_y())
        choice = Messagebox().show_question(
            message=tr('在关闭项目前，是否要保存项目？'),
            title=tr('关闭项目'),
            buttons=["{}:secondary".format(tr('取消'))," {} :secondary".format(tr('否'))," {} :primary".format(tr('是'))],
            alert=True,
            parent=toplevel,
            #width=10,
            position=(x+w,y+h)
            )
        if choice == ' {} '.format(tr('是')):
            self.save_file()
        elif choice == ' {} '.format(tr('否')):
            pass
        else:
            return
        # 关闭项目视图，返回首页
        self.master.close_project_view()
    # 加载封面
    def load_cover(self):
        SZ_300 = int(self.sz * 300)
        SZ_180 = int(self.sz * 168.75)
        try:
            image = Image.open(self.project.config.Cover).resize([960,540]).convert('RGBA')
        except Exception as E:
            cover_path = f'./assets/default_cover/{preference.theme}.jpg'
            image = Image.open(cover_path).convert('RGBA')
        # 渲染标题
        title = Image.new("RGBA",size=(960,128),color='#c3c3c3c3')
        draw = ImageDraw.Draw(title)
        title_font = ImageFont.truetype('./assets/SourceHanSerifSC-Heavy.otf',size=80)
        draw.text((20,0),text=self.project.config.Name,font=title_font,fill='#1e1e1eff')
        # 合并
        image.paste(title,(0,412),mask=title)
        self.cover = ImageTk.PhotoImage(image=image.resize([SZ_300,SZ_180]))
        self.title_pic.configure(image=self.cover)
    # 刷新目前某一类标签页的显示，导入文件时需要调用
    def update_pages_elements(self,ftype='medef'):
        # -> page_frame
        return self.page_frame.update_pages_elements(ftype)
    # 写入最近使用的文件
    def write_recent_project(self,name,path):
        list_of_project:list = Link['recent_files'] # 前4个
        text = name + '\t' + path
        if text in list_of_project:
            list_of_project.remove(text)
        elif len(list_of_project)>=5:
            list_of_project.pop(-1)
        else:
            pass
        list_of_project.insert(0,text)
# 项目视图-可折叠类容器-基类
class FileCollapsing(ttk.Frame):
    def __init__(self,master,screenzoom:float,fileclass:str,content,page_frame:PageFrame):
        self.sz = screenzoom
        self.page_frame = page_frame
        SZ_5 = int(self.sz * 10)
        SZ_2 = int(self.sz * 2)
        super().__init__(master=master,borderwidth=0)
        self.class_text = {'mediadef':tr('媒体库'),'chartab':tr('角色配置'),'rplgenlog':tr('剧本文件')}[fileclass]
        self.collapbutton = ttk.Button(master=self,text='▼ '+self.class_text,command=self.update_toggle,style='warning',cursor='hand2')
        self.content_frame = ttk.Frame(master=self)
        self.button_padding = (SZ_5,SZ_2,SZ_5,SZ_2)
        # 内容，正常来说，self.items的key应该正好等于Button的text
        self.content = content
        self.items = {}
    def update_item(self):
        SZ_1 = int(self.sz * 1)
        self.update_filelist()
        self.collapbutton.pack(fill='x',side='top',ipady=SZ_1)
        self.expand:bool = False
        self.update_toggle()
    def update_filelist(self):
        for idx in self.items:
            this_button:ttk.Button = self.items[idx]
            this_button.pack_forget()
            this_button.pack(fill='x',side='top')
    def update_toggle(self):
        if self.expand:
            self.content_frame.pack_forget()
            self.collapbutton.configure(text='▲ '+self.class_text)
            self.expand:bool = False
        else:
            self.content_frame.pack(fill='x',side='top')
            self.collapbutton.configure(text='▼ '+self.class_text)
            self.expand:bool = True
    def right_click_menu(self,event):
        # 获取关键字
        keyword = event.widget.cget('text')
        menu = ttk.Menu(master=self.content_frame,tearoff=0)
        menu.add_command(label=tr("重命名"),command=lambda:self.rename_item(keyword))
        menu.add_command(label=tr("删除"),command=lambda:self.delete_item(keyword))
        sort_menu = ttk.Menu(master=menu,tearoff=0)
        sort_menu.add_command(label=tr("正序"),command=lambda:self.sort_item(ascending=True))
        sort_menu.add_command(label=tr("倒序"),command=lambda:self.sort_item(ascending=False))
        menu.add_cascade(label=tr("排序"),menu=sort_menu)
        # 显示菜单
        menu.post(event.x_root, event.y_root)
    def add_item(self):
        # 取消收缩
        if self.expand is False:
            self.update_toggle()
        # 名字
        self.re_name = tk.StringVar(master=self,value='')
        self.in_rename:bool = True
        # 新建输入框
        new_entry:ttk.Entry = ttk.Entry(master=self.content_frame,textvariable=self.re_name,bootstyle='warning',justify='center')
        new_entry.bind("<Return>",lambda event:self.add_item_done(True))
        new_entry.bind("<FocusOut>",lambda event:self.add_item_done(False))
        new_entry.bind("<Escape>",lambda event:self.add_item_done(False))
        # 放置元件
        self.items['new:init'] = new_entry
        self.update_filelist()
        new_entry.focus_set()
    def add_item_failed(self):
        self.items['new:init'].destroy()
        self.items.pop('new:init')
        self.update_filelist()
    def add_item_done(self,enter,filetype=tr('角色'))->bool:
        new_keyword = self.re_name.get()
        origin_keyword = 'new:init'
        # 每次rename，done只能触发一次！
        if self.in_rename:
            self.in_rename = False
        else:
            return False
        try:
            if enter is False:
                self.add_item_failed()
                raise Exception('没有按回车键')
            if re.match('^[\w\ ]+$',new_keyword) is None:
                Messagebox().show_warning(
                    message = tr('非法的{type}名：{name}\n{type}名只能包含中文、英文、数字、下划线和空格！').format(type=filetype, name=new_keyword),
                    title   = tr('失败的新建'),
                    parent  = self.items[origin_keyword]
                    )
                self.add_item_failed()
                raise Exception('非法名')
            if new_keyword in self.items.keys():
                Messagebox().show_warning(
                    message = tr('重复的{type}名：{name}！').format(type=filetype, name=new_keyword),
                    title   = tr('失败的新建'),
                    parent  = self.items[origin_keyword]
                    )
                self.add_item_failed()
                raise Exception('重复名')
            # 删除原来的关键字
            self.items[origin_keyword].destroy()
            self.items.pop(origin_keyword)
            # 新建button
            self.create_new_button(new_keyword)
            self.update_filelist()
            # 返回值：是否会变更项目
            return True
        except Exception as E:
            return False
    def create_new_button(self,new_keyword:str):
        # 新建button
        self.items[new_keyword] = ttk.Button(
            master      = self.content_frame,
            text        = new_keyword,
            image       = self.img_name,
            bootstyle   = 'light',
            padding     = self.button_padding,
            compound    = 'left',
            )
        self.items[new_keyword].bind("<Button-1>",self.open_item_as_page)
        self.items[new_keyword].bind("<Button-3>",self.right_click_menu)
        self.update_filelist()
    def delete_item(self,keyword)->bool:
        # 确定真的要这么做吗？
        choice = Messagebox().show_question(
            message=tr('确定要删除这个条目？\n这项删除将无法复原！'),
            title=tr('警告'),
            buttons=[tr('取消')+":primary", tr('确定')+":danger"],
            parent=self.items[keyword]
            )
        # 返回是否需要删除项目数据
        if choice != tr('确定'):
            return False
        else:
            self.items[keyword].destroy()
            self.items.pop(keyword)
            return True
    def rename_item(self,keyword,filetype=tr('角色')):
        # 如果尝试重命名的是一个已经打开的标签页
        rename_an_active_page:bool = filetype+"-"+keyword in self.page_frame.page_dict.keys()
        if rename_an_active_page:
            choice = Messagebox().show_question(
                message=tr('尝试重命名一个已经启动的{}页面！\n重命名后，这个页面会被关闭！').format(filetype),
                title=tr('警告'),
                buttons=[tr('取消')+":primary", tr('确定')+":danger"],
                parent=self.items[keyword]
                )
            if choice != tr('确定'):
                return
        # 原来的按钮
        self.button_2_rename:ttk.Button = self.items[keyword]
        self.re_name = tk.StringVar(master=self,value=keyword)
        self.in_rename:bool = True
        # 新建输入框
        rename_entry:ttk.Entry = ttk.Entry(master=self.content_frame,textvariable=self.re_name,bootstyle='warning',justify='center',)
        rename_entry.bind("<Return>",lambda event:self.rename_item_done(True))
        rename_entry.bind("<FocusOut>",lambda event:self.rename_item_done(False))
        rename_entry.bind("<Escape>",lambda event:self.rename_item_done(False))
        # 放置元件
        self.items[keyword] = rename_entry
        # 更新
        self.button_2_rename.pack_forget()
        self.update_filelist()
        # 设置焦点
        rename_entry.focus_set()
    def rename_item_failed(self,origin_keyword):
        self.items[origin_keyword].destroy()
        self.items[origin_keyword] = self.button_2_rename
        self.update_filelist()
    def rename_item_done(self,enter:bool,filetype=tr('角色')):
        # 关键字
        origin_keyword = self.button_2_rename.cget('text')
        new_keyword = self.re_name.get()
        # 每次rename，done只能触发一次！
        if self.in_rename:
            self.in_rename = False
        else:
            return False
        try:
            if enter is False:
                # 删除Entry，复原Button
                self.rename_item_failed(origin_keyword)
                raise Exception('没有按回车键')
            if re.match('^[\w\ ]+$',new_keyword) is None:
                Messagebox().show_warning(
                    message = tr('非法的{type}名：{name}\n{type}名只能包含中文、英文、数字、下划线和空格！').format(type=filetype, name=new_keyword),
                    title   = tr('失败的重命名'),
                    parent  = self.items[origin_keyword]
                    )
                self.rename_item_failed(origin_keyword)
                raise Exception('非法名')
            if new_keyword in self.items.keys() and new_keyword != origin_keyword:
                Messagebox().show_warning(
                    message = tr('重复的{type}名：{name}\n！').format(type=filetype, name=new_keyword),
                    title   = tr('失败的重命名'),
                    parent  = self.items[origin_keyword]
                    )
                self.rename_item_failed(origin_keyword)
                raise Exception('重复名')
            # 如果新名字和旧名字一模一样，那就什么什么都不做，直接return False
            if new_keyword == origin_keyword:
                self.rename_item_failed(origin_keyword)
                raise Exception('重复名')
            # 删除原来的关键字
            self.items[origin_keyword].destroy()
            self.items.pop(origin_keyword)
            # 修改Button的text
            self.button_2_rename.config(text=self.re_name.get())
            # 更新self.items
            self.items[new_keyword] = self.button_2_rename
            self.update_filelist()
            # 返回值：是否会变更项目
            return True
        except Exception as E:
            return False
    def open_item_as_page(self,keyword,image,file_type,file_index):
        # 检查是否是Page_frame中的活跃页
        if keyword not in self.page_frame.active_page:
            # 如果不是活动页，新增活跃页
            self.page_frame.add_active_page(
                name        = keyword,
                image       = image,
                file_type   = file_type,
                content_obj = self.content,
                content_type= file_index
                )
        else:
            # 如果是活动页，切换到活跃页
            self.page_frame.goto_page(name=keyword)
    def enhance_image(self,image):
        enhancer = ImageEnhance.Brightness(image)
        enhanced_image = enhancer.enhance(3)
        return enhanced_image
    def sort_item(self,ascending=True):
        # 排序
        list_index = list(self.items.keys())
        reversed = not ascending
        try:
            list_index = sorted(list_index, key=lambda x: pinyin.get(x), reverse=reversed)
        except Exception:
            list_index.sort(reverse=reversed)
        # 调整item
        for idx in list_index:
            self.items[idx] = self.items.pop(idx)
        # 显示
        self.update_filelist()
# 项目视图-可折叠类容器-媒体类
class MDFCollapsing(FileCollapsing):
    media_type_name = {
        'Pos'       :   '位置',
        'Text'      :   '字体',
        'Bubble'    :   '气泡',
        'Animation' :   '立绘',
        'Background':   '背景',
        'Audio'     :   '音频',
    }
    def __init__(self, master, screenzoom: float, content:MediaDef, page_frame:PageFrame):
        super().__init__(master, screenzoom, 'mediadef', content, page_frame)
        SZ_15 = int(self.sz * 15)
        icon_size = [SZ_15,SZ_15]
        self.image_path = {
            'Pos'       : './assets/icon/FM_pos.png',
            'Text'      : './assets/icon/FM_text.png',
            'Bubble'    : './assets/icon/FM_bubble.png',
            'Animation' : './assets/icon/FM_animation.png',
            'Background': './assets/icon/FM_background.png',
            'Audio'     : './assets/icon/FM_audio.png',
        }
        self.image = {}
        for mediatype in ['Pos', 'Text', 'Bubble', 'Animation', 'Background', 'Audio']:
            filename = self.media_type_name[mediatype]
            if preference.lang == 'zh':
                showname = "{} ({})".format(filename,mediatype)
            else:
                showname = mediatype
            if preference.theme == 'rplgendark':
                self.image[mediatype] = ImageTk.PhotoImage(name='FM_'+mediatype , image=self.enhance_image(Image.open(self.image_path[mediatype]).resize(icon_size)))
            else:
                self.image[mediatype] = ImageTk.PhotoImage(name='FM_'+mediatype , image=Image.open(self.image_path[mediatype]).resize(icon_size))
            self.image[mediatype+'_LT'] = ImageTk.PhotoImage(name='FM_'+mediatype+'_LT' , image=self.enhance_image(Image.open(self.image_path[mediatype]).resize(icon_size)))
            self.items[mediatype] = ttk.Button(
                master      = self.content_frame,
                text        = showname,
                image       = 'FM_'+mediatype,
                bootstyle   = 'light',
                padding     = self.button_padding,
                compound    = 'left',
                cursor      = 'hand2'
                )
            self.items[mediatype].bind("<Button-1>",self.open_item_as_page)
        self.update_item()
    def open_item_as_page(self,event):
        # 获取点击按钮的关键字
        keyword = event.widget.cget('text')
        if preference.lang == 'zh':
            filename,file_index = keyword.split(' ') # 前两个字
            file_index = file_index[1:-1] # 去除括号
        else:
            filename = keyword
            file_index = keyword
        super().open_item_as_page(
            keyword     = tr('媒体')+'-' + filename, # '媒体-立绘'
            image       = 'FM_' + file_index,
            file_type   = 'MDF',
            file_index  = file_index # 'Animation'
            )

# 项目视图-可折叠类容器-角色类
class CTBCollapsing(FileCollapsing):
    def __init__(self, master, screenzoom: float, content:CharTable, page_frame:PageFrame):
        super().__init__(master, screenzoom, 'chartab', content, page_frame)
        SZ_15 = int(self.sz * 15)
        SZ_10 = int(self.sz * 10)
        icon_size = [SZ_15,SZ_15]
        image = Image.open('./assets/icon/FM_charactor.png').resize(icon_size)
        if preference.theme == 'rplgendark':
            self.image = [
                ImageTk.PhotoImage(name='FM_charactor' , image=self.enhance_image(image)),
                ImageTk.PhotoImage(name='FM_charactor_LT' , image=self.enhance_image(image)),
                ]
        else:
            self.image = [
                ImageTk.PhotoImage(name='FM_charactor' , image=image),
                ImageTk.PhotoImage(name='FM_charactor_LT' , image=self.enhance_image(image)),
                ]
        self.img_name = 'FM_charactor'
        # 新建按钮
        self.add_button = ttk.Button(master=self.collapbutton,text=tr('新增+'),bootstyle='warning',padding=0,command=self.add_item,cursor='hand2')
        self.add_button.place(relx=0.8,relwidth=0.2, x=-SZ_10,rely=0.1,relheight=0.8)
        # self.add_button.pack(side='right',padx=SZ_10,pady=SZ_5,ipady=SZ_1,ipadx=SZ_3)
        self.table = self.content.export()
        # 内容
        for name in self.table['Name'].unique():
            self.items[name] = ttk.Button(
                master      = self.content_frame,
                text        = name,
                image       = self.img_name,
                bootstyle   = 'light',
                padding     = self.button_padding,
                compound    = 'left',
                cursor      = 'hand2'
                )
            self.items[name].bind("<Button-1>",self.open_item_as_page)
            self.items[name].bind("<Button-3>",self.right_click_menu)
        self.update_item()
    def add_item_done(self, enter):
        confirm_add =  super().add_item_done(enter, tr('角色'))
        new_keyword = self.re_name.get()
        if confirm_add:
            self.content.add_chara_default(new_keyword)
    def delete_item(self, keyword):
        confirm_delete:bool = super().delete_item(keyword)
        delete_an_active_page:bool = tr("角色") + "-"+keyword in self.page_frame.page_dict.keys()
        if confirm_delete:
            # 如果是激活的页面，关闭激活的标签页
            if delete_an_active_page:
                self.page_frame.page_notebook.delete(tr("角色")+"-"+keyword)
            # 执行删除项目
            self.content.delete_chara(name=keyword)
    def rename_item(self, keyword):
        return super().rename_item(keyword,filetype=tr('角色'))
    def rename_item_done(self,enter:bool):
        origin_keyword = self.button_2_rename.cget('text')
        new_keyword = self.re_name.get()
        rename_an_active_page:bool = tr("角色") + "-" + origin_keyword in self.page_frame.page_dict.keys()
        edit_CTB = super().rename_item_done(enter=enter,filetype=tr('角色'))
        if edit_CTB:
            if rename_an_active_page:
                self.page_frame.page_notebook.delete(tr("角色")+"-"+origin_keyword)
            # 重命名 content
            self.content.rename(origin_keyword,new_keyword)
            # 是否广播
            ask_rename_boardcast(master=self,old_name=origin_keyword,new_name=new_keyword,otype='name')
    def open_item_as_page(self,event):
        # 获取点击按钮的关键字
        keyword = event.widget.cget('text')
        super().open_item_as_page(
            keyword     = tr('角色') + '-'+keyword,
            image       = self.img_name,
            file_type   = 'CTB',
            file_index  = keyword
            )
    def get_chara_name(self)->list:
        return list(self.items.keys())
# 项目视图-可折叠类容器-剧本类
class RGLCollapsing(FileCollapsing): 
    def __init__(self, master, screenzoom: float, content:dict, page_frame:PageFrame):
        super().__init__(master, screenzoom, 'rplgenlog', content, page_frame)
        SZ_15 = int(self.sz * 15)
        SZ_10 = int(self.sz * 10)
        SZ_5  = int(self.sz * 5 )
        SZ_3  = int(self.sz * 3 )
        SZ_1  = int(self.sz * 1 )
        icon_size = [SZ_15,SZ_15]
        image = Image.open('./assets/icon/FM_logfile.png').resize(icon_size)
        if preference.theme == 'rplgendark':
            self.image = [
                ImageTk.PhotoImage(name='FM_logfile' , image=self.enhance_image(image)),
                ImageTk.PhotoImage(name='FM_logfile_LT' , image=self.enhance_image(image)),
                ]
        else:
            self.image = [
                ImageTk.PhotoImage(name='FM_logfile' , image=image),
                ImageTk.PhotoImage(name='FM_logfile_LT' , image=self.enhance_image(image)),
                ]
        self.img_name = 'FM_logfile'
        # 新建按钮
        self.add_button = ttk.Button(master=self.collapbutton,text=tr('新增+'),bootstyle='warning',padding=0,command=self.add_item,cursor='hand2')
        self.add_button.place(relx=0.8,relwidth=0.2, x=-SZ_10,rely=0.1,relheight=0.8)
        # self.add_button.pack(side='right',padx=SZ_10,pady=SZ_5,ipady=SZ_1,ipadx=SZ_3)
        # 内容
        for key in self.content.keys():
            self.items[key] = ttk.Button(
                master      = self.content_frame,
                text        = key,
                image       = self.img_name,
                bootstyle   = 'light',
                padding     = self.button_padding,
                compound    = 'left',
                cursor      = 'hand2'
                )
            self.items[key].bind("<Button-1>",self.open_item_as_page)
            self.items[key].bind("<Button-3>",self.right_click_menu)
        self.update_item()
    def add_item_done(self, enter):
        confirm_add =  super().add_item_done(enter, tr('剧本'))
        new_keyword = self.re_name.get()
        executable = sys.executable
        if confirm_add:
            # 新建一个空白的RGL
            self.content[new_keyword] = RplGenLog(
                string_input=tr('#! {executable}\n# {new_keyword}: 空白的剧本文件。点按键盘Tab键，获取命令智能补全。预览和导出按钮在右侧 ->\n').format(
                    executable=executable,
                    new_keyword=new_keyword
                )
                )
    def delete_item(self, keyword):
        confirm_delete:bool = super().delete_item(keyword)
        delete_an_active_page:bool = tr("剧本")+"-"+keyword in self.page_frame.page_dict.keys()
        if confirm_delete:
            # 如果是激活的页面，关闭激活的标签页
            if delete_an_active_page:
                self.page_frame.page_notebook.delete(tr("剧本")+"-"+keyword)
            # 执行删除项目
            self.content.pop(keyword)
    def rename_item(self, keyword):
        return super().rename_item(keyword,filetype=tr('剧本'))
    def rename_item_done(self,enter:bool):
        origin_keyword = self.button_2_rename.cget('text')
        new_keyword = self.re_name.get()
        rename_an_active_page:bool = tr("剧本") + "-"+origin_keyword in self.page_frame.page_dict.keys()
        edit_RGL = super().rename_item_done(enter=enter,filetype=tr('剧本'))
        if edit_RGL:
            if rename_an_active_page:
                self.page_frame.page_notebook.delete(tr("剧本")+"-"+origin_keyword)
            # 重命名 content
            self.content[new_keyword] = self.content[origin_keyword]
            self.content.pop(origin_keyword)
    def open_item_as_page(self,event):
        # 获取点击按钮的关键字
        keyword = event.widget.cget('text')
        super().open_item_as_page(
            keyword     = tr("剧本")+"-"+keyword,
            image       = self.img_name,
            file_type   = 'RGL',
            file_index  = keyword
            )