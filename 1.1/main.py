#mPythonType:0
#mPythonType:0
from mpython import *
from framebuf import FrameBuffer
import framebuf
import time, uos, urandom
import music
import _thread
import network
import bluetooth

# 新增蓝牙扫描相关
ble = bluetooth.BLE()
ble.active(True)

BIRD = bytearray([
    0x7, 0xe0, 0x18, 0xf0, 0x21, 0xf8, 0x71, 0xec, 0xf9, 0xec, 0xfc, 0xfc, 0xbe, 0x7e, 0x4c, 0x81, 0x71, 0x7e, 0x40,
    0x82, 0x30, 0x7c, 0xf, 0x80
])
PIPE_TOP = bytearray([
    0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20,
    0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c,
    0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20,
    0x1c, 0xff, 0xff, 0x80, 0xf, 0x80, 0xf, 0x80, 0xf, 0x80, 0xf, 0xff, 0xff
])
PIPE_DOWN = bytearray([
    0xff, 0xff, 0x80, 0xf, 0x80, 0xf, 0x80, 0xf, 0x80, 0xf, 0xff, 0xff, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c,
    0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20,
    0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c,
    0x20, 0x1c, 0x20, 0x1c, 0x20, 0x1c
])
bird_size = (16, 12)
pipe_size = (16, 32)
WIDTH = 128
HEIGHT = 64
class Bird:
    def __init__(self):
        self.height = bird_size[1]
        self.y = HEIGHT // 2 - self.height // 2
        self.wing_power = 4
        self.gravity = 0.8
        self.vel = -self.wing_power
    def drop(self):
        self.vel += self.gravity
        self.y = int(self.y + self.vel)
    def flap(self):
        self.vel = -self.wing_power
    def crashed(self):
        y_limit = HEIGHT - self.height
        return self.y > y_limit
class Obstacle:
    def __init__(self, x, size):
        self.size = size
        self.gap = urandom.randint(6 + self.size, HEIGHT - 6 - self.size)
        self.x = x
        self.score = 0
        self.rate = 3

    def scroll(self):
        self.x -= self.rate
        if self.x < -pipe_size[0]:
            self.score += 1
            self.x = WIDTH
            self.gap = urandom.randint(6 + self.size, HEIGHT - 6 - self.size)

    def collided(self, y):
        if self.x < bird_size[0] and self.x > -pipe_size[0] and \
           (self.gap - y > self.size or y + bird_size[1] - self.gap > self.size):
            return True
        else:
            return False
class Game:
    def __init__(self, gap_size):
        self.bird_fb = FrameBuffer(BIRD, bird_size[0], bird_size[1], framebuf.MONO_HLSB)
        self.pipe_top_fb = FrameBuffer(PIPE_TOP, pipe_size[0], pipe_size[1], framebuf.MONO_HLSB)
        self.pipe_down_fb = FrameBuffer(PIPE_DOWN, pipe_size[0], pipe_size[1], framebuf.MONO_HLSB)
        self.gap_size = gap_size
        self.high_score = 0
        self.pressed = False
        self.game_state = 0
        self.flappy_bird = None
        self.obstacle_1 = None
        self.obstacle_2 = None
    def write_high_score(self, n):
        f = open('fb_high_score.txt', 'w')
        f.write(str(n))
        f.close()
    def read_high_score(self):
        if 'fb_high_score.txt' in uos.listdir():
            f = open('fb_high_score.txt', 'r')
            high_score = f.read()
            f.close()
            return int(high_score)
        else:
            self.write_high_score(0)
            return 0
    def draw(self):
        oled.fill(0)
        oled.blit(self.bird_fb, 0, self.flappy_bird.y)
        oled.blit(self.pipe_top_fb, self.obstacle_1.x, self.obstacle_1.gap - self.gap_size - pipe_size[1])
        oled.blit(self.pipe_down_fb, self.obstacle_1.x, self.obstacle_1.gap + self.gap_size)
        oled.blit(self.pipe_top_fb, self.obstacle_2.x, self.obstacle_2.gap - self.gap_size - pipe_size[1])
        oled.blit(self.pipe_down_fb, self.obstacle_2.x, self.obstacle_2.gap + self.gap_size)
        oled.fill_rect(WIDTH // 2 - 13, 0, 26, 9, 0)
        oled.text('%03d' % (self.obstacle_1.score + self.obstacle_2.score), WIDTH // 2 - 12, 0)
        oled.show()
    def _clicked(self):
        if button_a.value() == 0 and not self.pressed:
            self.pressed = True
            return True
        elif button_a.value() == 1 and self.pressed:
            self.pressed = False
        if button_b.value() == 0 and not self.pressed:
            self.write_high_score(0)
        return False
    def game_start(self):
        self.high_score = self.read_high_score()
        oled.fill(0)
        oled.blit(self.pipe_down_fb, (WIDTH - pipe_size[0]) // 2, HEIGHT - 12)
        oled.blit(self.bird_fb, (WIDTH - bird_size[0]) // 2, HEIGHT - 12 - bird_size[1])
        oled.rect(0, 0, WIDTH, HEIGHT, 1)
        oled.text('F L A P P Y', WIDTH // 2 - 44, 3)
        oled.text('B I R D', WIDTH // 2 - 28, 13)
        oled.text('Record: ' + '%03d' % self.high_score, WIDTH // 2 - 44, HEIGHT // 2 - 6)
        oled.show()
        self.game_state = 1
    def game_waiting(self):
        if self._clicked():
            self.flappy_bird = Bird()
            self.obstacle_1 = Obstacle(WIDTH, self.gap_size)
            self.obstacle_2 = Obstacle(WIDTH + (WIDTH + pipe_size[0]) // 2, self.gap_size)
            self.game_state = 2
    def game_running(self):
        if self._clicked():
            self.flappy_bird.flap()
        self.flappy_bird.drop()
        if self.flappy_bird.crashed():
            self.flappy_bird.y = HEIGHT - self.flappy_bird.height
            self.game_state = 3
        self.obstacle_1.scroll()
        self.obstacle_2.scroll()
        if self.obstacle_1.collided(self.flappy_bird.y) or self.obstacle_2.collided(self.flappy_bird.y):
            self.game_state = 3
        self.draw()
    def game_over(self):
        oled.fill_rect(WIDTH // 2 - 32, 10, 64, 23, 0)
        oled.rect(WIDTH // 2 - 32, 10, 64, 23, 1)
        oled.text('G A M E', WIDTH // 2 - 28, 13)
        oled.text('O V E R', WIDTH // 2 - 28, 23)
        self.score = self.obstacle_1.score + self.obstacle_2.score
        if self.score > self.high_score:
            self.high_score = self.score
            oled.fill_rect(WIDTH // 2 - 48, 37, 96, 14, 0)
            oled.rect(WIDTH // 2 - 48, 37, 96, 14, 1)
            oled.text('New Record!', WIDTH // 2 - 44, 40)
            self.write_high_score(self.high_score)
        oled.show()
        self.game_state = 1
    def run(self):
        while True:
            if touchpad_p.is_pressed() or touchpad_y.is_pressed() or touchpad_t.is_pressed() or touchpad_h.is_pressed() or touchpad_o.is_pressed() or touchpad_n.is_pressed():
                oled.fill(0)
                oled.DispChar(str(menu[menu_index]), 0, 0, 1)
                oled.show()
                break
            if self.game_state == 0: self.game_start()
            elif self.game_state == 1: self.game_waiting()
            elif self.game_state == 2: self.game_running()
            elif self.game_state == 3: self.game_over()

def my_1_():
    global menu_index, music_index, dengguang, tanzou, musiclist, menu, clock_time, start_time
    music.play('C4:2')
def my_2_():
    global menu_index, music_index, dengguang, tanzou, musiclist, menu, clock_time, start_time
    music.play('D4:2')
def my_3_():
    global menu_index, music_index, dengguang, tanzou, musiclist, menu, clock_time, start_time
    music.play('E4:2')
def my_4_():
    global menu_index, music_index, dengguang, tanzou, musiclist, menu, clock_time, start_time
    music.play('F4:2')
def my_5_():
    global menu_index, music_index, dengguang, tanzou, musiclist, menu, clock_time, start_time
    music.play('G4:2')
def my_6_():
    global menu_index, music_index, dengguang, tanzou, musiclist, menu, clock_time, start_time
    music.play('A4:2')
def my_7_():
    global menu_index, music_index, dengguang, tanzou, musiclist, menu, clock_time, start_time
    music.play('B4:2')
def my_1_5E():
    global menu_index, music_index, dengguang, tanzou, musiclist, menu, clock_time, start_time
    music.play('C5:2')
def my_2_5E():
    global menu_index, music_index, dengguang, tanzou, musiclist, menu, clock_time, start_time
    music.play('D5:2')
def my_0_():
    global menu_index, music_index, dengguang, tanzou, musiclist, menu, clock_time, start_time
    time.sleep(0.25)
def my_3_5E():
    global menu_index, music_index, dengguang, tanzou, musiclist, menu, clock_time, start_time
    music.play('E5:2')
def my_4_5E():
    global menu_index, music_index, dengguang, tanzou, musiclist, menu, clock_time, start_time
    music.play('F5:2')
def _E6_92_AD_E6_94_BE_E9_BB_91_E4_BA_BA_E6_8A_AC_E6_A3_BA():
    global menu_index, music_index, dengguang, tanzou, musiclist, menu, clock_time, start_time
    for count in range(16):
        music.play('D4:2')
    for count in range(36):
        music.play('F4:2')
    for count in range(4):
        music.play('A4:2')
    for count in range(4):
        music.play('G4:2')
    for count in range(4):
        music.play('C5:2')
    for count in range(12):
        music.play('D5:2')
    my_5_()
    my_4_()
    my_3_()
    my_1_()
    my_2_()
    my_0_()
    my_2_()
    my_6_()
    my_5_()
    my_0_()
    my_4_()
    my_0_()
    my_3_()
    my_0_()
    my_3_()
    my_3_()
    my_5_()
    my_0_()
    my_4_()
    my_3_()
    for count in range(2):
        for count in range(2):
            my_2_()
            my_0_()
            my_2_()
            my_4_5E()
            my_3_5E()
            my_4_5E()
            my_3_5E()
            my_4_5E()
        my_2_()
        my_0_()
        my_2_()
        my_6_()
        my_5_()
        my_0_()
        my_4_()
        my_0_()
        my_3_()
        my_0_()
        my_3_()
        my_3_()
        my_5_()
        my_0_()
        my_4_()
        my_3_()
    for count in range(2):
        my_2_()
        my_0_()
        my_2_()
        my_4_5E()
        my_3_5E()
        my_4_5E()
        my_3_5E()
        my_4_5E()
    for count in range(4):
        my_4_()
    for count in range(4):
        my_6_()
    for count in range(4):
        my_5_()
    for count in range(4):
        my_1_5E()
    for count in range(10):
        my_2_5E()

def show_wifi():
    wlan = network.WLAN(network.STA_IF)
    # 开启WiFi调制解调器睡眠功能
    wlan.config(pm = network.WIFI_PM_PERFORMANCE)
    wlan.active(True)
    aps = wlan.scan()
    page = 0
    while True:
        start = page * 7
        end = start + 7
        oled.fill(0)
        for i, ap in enumerate(aps[start:end]):
            ssid = ap[0].decode()
            rssi = str(ap[3])
            oled.text(ssid+" ("+rssi+"dBm)", 0, i * 10)
        oled.show()
        if button_a.is_pressed():
            time.sleep(0.3)
            if start + 7 < len(aps):
                page += 1
        if button_b.is_pressed():
            time.sleep(0.3)
            break

def show_ble():
    scan_results = []
    def adv_callback(event, data):
        if event == bluetooth.SCAN_RESULT:
            addr_type, addr, adv_type, rssi, adv_data = data
            scan_results.append((addr, rssi))
    ble.irq(adv_callback)
    ble.gap_scan(2000, 30000, 30000)
    time.sleep(2)
    ble.gap_scan(None)
    page = 0
    while True:
        start = page * 7
        end = start + 7
        oled.fill(0)
        for i, (addr, rssi) in enumerate(scan_results[start:end]):
            addr_str = ':'.join('{:02x}'.format(x) for x in addr)
            rssi_str = str(rssi)
            oled.text(addr_str+" ("+rssi_str+"dBm)", 0, i * 10)
        oled.show()
        if button_a.is_pressed():
            time.sleep(0.3)
            if start + 7 < len(scan_results):
                page += 1
        if button_b.is_pressed():
            time.sleep(0.3)
            break

def thread_1():
    global start_time, clock_time, menu, musiclist, tanzou, dengguang, music_index, menu_index
    music_index = 0
    musiclist = ["东方红","黑人抬棺","歌唱祖国","彩云追月","茉莉花","沂蒙山小调","生日歌","DADADADUM","退出"]
    while True:
        if button_a.is_pressed():
            if menu_index == len(menu) - 1:
                menu_index = 0
            else:
                menu_index = menu_index + 1
            oled.fill(0)
            oled.DispChar(str(menu[menu_index]), 0, 0, 1)
            oled.show()
        if button_b.is_pressed():
            if menu_index == 0:
                if dengguang == 0:
                    dengguang = 1
                    rgb.fill( (int(255), int(255), int(255)) )
                    rgb.write()
                    time.sleep_ms(1)
                else:
                    dengguang = 0
                    rgb.fill( (0, 0, 0) )
                    rgb.write()
                    time.sleep_ms(1)
            if menu_index == 1:
                if tanzou == 0:
                    tanzou = 1
                else:
                    tanzou = 0
            if menu_index == 2:
                time.sleep(0.3)
                oled.fill(0)
                oled.DispChar(str(musiclist[music_index]), 0, 0, 1)
                oled.show()
                while True:
                    if button_a.is_pressed():
                        if music_index == len(musiclist) - 1:
                            music_index = 0
                        else:
                            music_index = music_index + 1
                        oled.fill(0)
                        oled.DispChar(str(musiclist[music_index]), 0, 0, 1)
                        oled.show()
                    if button_b.is_pressed():
                        if music_index == 0:
                            music.play(music.DONG_FANG_HONG, wait=True, loop=False)
                            break
                        if music_index == 1:
                            for count in range(16):
                                music.play('D4:2')
                            for count in range(36):
                                music.play('F4:2')
                            for count in range(4):
                                music.play('A4:2')
                            for count in range(4):
                                music.play('G4:2')
                            for count in range(4):
                                music.play('C5:2')
                            for count in range(12):
                                music.play('D5:2')
                            my_5_()
                            my_4_()
                            my_3_()
                            my_1_()
                            my_2_()
                            my_0_()
                            my_2_()
                            my_6_()
                            my_5_()
                            my_0_()
                            my_4_()
                            my_0_()
                            my_3_()
                            my_0_()
                            my_3_()
                            my_3_()
                            my_5_()
                            my_0_()
                            my_4_()
                            my_3_()
                            for count in range(2):
                                for count in range(2):
                                    my_2_()
                                    my_0_()
                                    my_2_()
                                    my_4_5E()
                                    my_3_5E()
                                    my_4_5E()
                                    my_3_5E()
                                    my_4_5E()
                                my_2_()
                                my_0_()
                                my_2_()
                                my_6_()
                                my_5_()
                                my_0_()
                                my_4_()
                                my_0_()
                                my_3_()
                                my_0_()
                                my_3_()
                                my_3_()
                                my_5_()
                                my_0_()
                                my_4_()
                                my_3_()
                            for count in range(2):
                                my_2_()
                                my_0_()
                                my_2_()
                                my_4_5E()
                                my_3_5E()
                                my_4_5E()
                                my_3_5E()
                                my_4_5E()
                            for count in range(4):
                                my_4_()
                            for count in range(4):
                                my_6_()
                            for count in range(4):
                                my_5_()
                            for count in range(4):
                                my_1_5E()
                            for count in range(10):
                                my_2_5E()
                            break
                        if music_index == 2:
                            music.play(music.GE_CHANG_ZU_GUO, wait=True, loop=False)
                            break
                        if music_index == 3:
                            music.play(music.CAI_YUN_ZHUI_YUE, wait=True, loop=False)
                            break
                        if music_index == 4:
                            music.play(music.MO_LI_HUA, wait=True, loop=False)
                            break
                        if music_index == 5:
                            music.play(music.YI_MENG_SHAN_XIAO_DIAO, wait=True, loop=False)
                            break
                        if music_index == 6:
                            music.play(music.BIRTHDAY, wait=True, loop=False)
                            break
                        if music_index == 7:
                            music.play(music.DADADADUM, wait=True, loop=False)
                            break
                        if music_index == 8:
                            break
                oled.fill(0)
                oled.DispChar(str(menu[menu_index]), 0, 0, 1)
                oled.show()
            if menu_index == 3:
                clock_time = 9
                if 0 == 0:
                    oled.fill(0)
                    oled.DispChar(str(str('预设') + str(str(clock_time) + str('小时'))), 0, 0, 1)
                    oled.DispChar(str('P减小1h Y增加1h H减小6m O增加6m T开始'), 0, 16, 1, True)
                    oled.show()
                    while not touchpad_t.is_pressed():
                        if touchpad_p.is_pressed():
                            clock_time = clock_time + -1
                            oled.fill(0)
                            oled.DispChar(str(str('预设') + str(str(clock_time) + str('小时'))), 0, 0, 1)
                            oled.DispChar(str('P减小1h Y增加1h H减小6m O增加6m T开始'), 0, 16, 1, True)
                            oled.show()
                            time.sleep(0.1)
                        if touchpad_y.is_pressed():
                            clock_time = clock_time + 1
                            oled.fill(0)
                            oled.DispChar(str(str('预设') + str(str(clock_time) + str('小时'))), 0, 0, 1)
                            oled.DispChar(str('P减小1h Y增加1h H减小6m O增加6m T开始'), 0, 16, 1, True)
                            oled.show()
                            time.sleep(0.1)
                        if touchpad_h.is_pressed():
                            clock_time = clock_time + -0.1
                            oled.fill(0)
                            oled.DispChar(str(str('预设') + str(str(clock_time) + str('小时'))), 0, 0, 1)
                            oled.DispChar(str('P减小1h Y增加1h H减小6m O增加6m T开始'), 0, 16, 1, True)
                            oled.show()
                            time.sleep(0.1)
                        if touchpad_o.is_pressed():
                            clock_time = clock_time + 0.1
                            oled.fill(0)
                            oled.DispChar(str(str('预设') + str(str(clock_time) + str('小时'))), 0, 0, 1)
                            oled.DispChar(str('P减小1h Y增加1h H减小6m O增加6m T开始'), 0, 16, 1, True)
                            oled.show()
                            time.sleep(0.1)
                start_time = time.time()
                while not (start_time + int((clock_time * 3600))) - time.time() <= 3:
                    oled.fill(0)
                    oled.DispChar(str((str((start_time + int((clock_time * 3600))) - time.time()))), 0, 16, 1)
                    oled.show()
                    time.sleep(1)
                oled.fill(0)
                oled.DispChar(str('时间到'), 0, 0, 1)
                oled.show()
                for count in range(2):
                    music.play(music.DADADADUM, wait=True, loop=False)
                    music.play(music.POWER_UP, wait=True, loop=False)
                    music.play(music.POWER_DOWN, wait=True, loop=False)
                    for freq in range(20, 2000, 10):
                        music.pitch(freq, 20)
                    _E6_92_AD_E6_94_BE_E9_BB_91_E4_BA_BA_E6_8A_AC_E6_A3_BA()
                oled.fill(0)
                oled.DispChar(str(menu[menu_index]), 0, 0, 1)
                oled.show()
            if menu_index == 4:
                game = Game(gap_size=16)
                game.run()
            if menu_index == 5:
                show_wifi()
            if menu_index == 6:
                show_ble()
            time.sleep(0.3)

menu_index = 0
dengguang = 0
tanzou = 0
menu = ["灯光", "弹奏", "预设乐谱", "闹钟", "飞行小鸟", "wifi显示", "蓝牙显示"]
oled.fill(0)
oled.DispChar(str(menu[menu_index]), 0, 0, 1)
oled.show()
music.set_tempo(ticks=4, bpm=120)
_thread.start_new_thread(thread_1, ())

while True:
    if touchpad_p.is_pressed() and tanzou == 1:
        music.play('C4:2')
    if touchpad_y.is_pressed() and tanzou == 1:
        music.play('D4:2')
    if touchpad_t.is_pressed() and tanzou == 1:
        music.play('E4:2')
    if touchpad_h.is_pressed() and tanzou == 1:
        music.play('F4:2')
    if touchpad_o.is_pressed() and tanzou == 1:
        music.play('G4:2')
    if touchpad_n.is_pressed() and tanzou == 1:
        music.play('A4:2')
