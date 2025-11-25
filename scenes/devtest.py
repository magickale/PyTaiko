from pathlib import Path
import pyray as ray

from libs.screen import Screen
from libs.texture import tex


class DevScreen(Screen):
    def on_screen_start(self):
        super().on_screen_start()
        self.text = ".⁉ゃん座組ス5れへデ7？x事音ょ野ダHズパに相村束虹神狂'Uqはたt朗♢弥ウち”作Wシら黒さドカモ金章よ方りj沙べ口ぃご歌！こ制みわ険時行×ワ獣ぺ阿啓R哀肉乱終鼓ツ,0かVしでw?2⒒悟マ乙ィの女アラA疾浄u+も’グ怒[ャロ冒陽ね路想ベ#ト醜ペ!太悪χキn初あKン〜<原Qハ1s旅をガ分ビNゼ玄沢≠食@フ拝テM豚幻濤ま人腹世P愴)っピやナJ社びB一6c畑譚]gてd～曲花Oくkル第◇校*⒓森・バコ談ヤ急め愛プ重ー勝DE:Zチ東二じ車>ブ刑ミ＋X：焼おyつλ♪オい憎aFe竜そ大84得渉/◆ソC番、l†レ悲暴う胸るG“ゆS転fゅとセo「風輔＠双zr―-vノケp‼b…響3メ罪 クL自(Iイタニムき夜幽T&楽m学走ジ島h田i美心Yボサッリュひ寅9」達"
        unique_codepoints = set(self.text)
        codepoint_count = ray.ffi.new('int *', 0)
        unique_string = ''.join(unique_codepoints)
        codepoints = ray.load_codepoints(unique_string, codepoint_count)
        self.font = ray.load_font_ex(str(Path('Graphics/Modified-DFPKanteiryu-XB.ttf')), 40, codepoints, len(unique_codepoints))

    def on_screen_end(self, next_screen: str):
        return super().on_screen_end(next_screen)

    def update(self):
        super().update()

    def draw(self):
        ray.draw_rectangle(0, 0, tex.screen_width, tex.screen_height, ray.GREEN)
        ray.draw_text_ex(self.font, "幽玄ノ乱", ray.Vector2(tex.screen_width//2, tex.screen_height//2), 60, 20, ray.BLACK)
