def font_init(self):
    # 字体
    # 系统字体
    system_font_family = {
        'zh': {
            'win32': 'Microsoft YaHei UI',
            'linux': '文泉驿微米黑',
            'darwin': '华文黑体',
            'else': '华文黑体'
        },
        # TODO: 英文
        'en': {
            
        }
    }
    font_platforms: dict = system_font_family.get(preference.lang, system_font_family['zh'])
    self.system_font_family = font_platforms.get(sys.platform, font_platforms['else'])
    Link['system_font_family'] = self.system_font_family
    # 终端字体
    ## 由于steam库目录有时会存在空格, 导致无法正常加载字体。虽然令人费解, 但是还是要想想办法
    def zh_terminal_font_family():
        try:
            from tkextrafont import Font as FileFont
            terminal_font = FileFont(file='./assets/sarasa-mono-sc-regular.ttf')
            terminal_font_family = 'Sarasa Mono SC'
        except Exception as E:
            print('terminal font family set error, using system font family instead\n',E)
            terminal_font_family = system_font_family
        return terminal_font, terminal_font_family
    
    terminal_font_family = {
        'zh': zh_terminal_font_family,
        'else': zh_terminal_font_family,
    }
    self.terminal_font, self.terminal_font_family = terminal_font_family.get(preference.lang, terminal_font_family['else'])()
    Link['terminal_font_family'] = self.terminal_font_family