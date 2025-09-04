import os
import subprocess
import threading
import arabic_reshaper
from bidi.algorithm import get_display

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.lang import Builder

# --- إعدادات التصميم واللغة العربية ---
# 1. تحميل الخط العربي
#    تأكد من وجود ملف الخط "Cairo-Regular.ttf" في نفس المجلد
ARABIC_FONT = "font.ttf"

# 2. دالة لمعالجة النصوص العربية للعرض الصحيح
def shape_arabic(text):
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

# 3. تصميم Kivy (KV Language) لتطبيق تصميم النيون
KV_DESIGN = """
<NeonButton@Button>:
    font_name: app.arabic_font
    font_size: '20sp'
    background_color: (0, 0, 0, 0) # خلفية شفافة
    background_normal: ''
    canvas.before:
        Color:
            rgba: (0.3, 0.7, 1, 1) if self.state == 'normal' else (0.1, 0.4, 0.7, 1) # لون أزرق فاتح
        RoundedRectangle:
            size: self.size
            pos: self.pos
            radius: [10]
        Color:
            rgba: (0, 0, 0, 1) # لون داخلي داكن
        RoundedRectangle:
            size: [self.size[0] - 4, self.size[1] - 4]
            pos: [self.pos[0] + 2, self.pos[1] + 2]
            radius: [8]

<NeonLabel@Label>:
    font_name: app.arabic_font
    color: (0.7, 0.9, 1, 1) # لون النص أزرق فاتح جداً

<NeonTextInput@TextInput>:
    font_name: app.arabic_font
    background_color: (0.1, 0.1, 0.1, 1)
    foreground_color: (0.8, 1, 1, 1)
    cursor_color: (0.3, 0.7, 1, 1)
    hint_text_color: (0.4, 0.4, 0.4, 1)
    multiline: False
    font_size: '18sp'

BoxLayout:
    orientation: 'vertical'
    padding: 30
    spacing: 20
    canvas.before:
        Color:
            rgba: (0.05, 0.05, 0.1, 1) # خلفية داكنة جداً
        Rectangle:
            pos: self.pos
            size: self.size

    NeonLabel:
        text: app.shape(app.title_text)
        font_size: '28sp'
        bold: True
        size_hint_y: 0.2

    NeonTextInput:
        id: url_input
        hint_text: app.shape("ألصق الرابط هنا")
        
    NeonButton:
        id: fetch_button
        text: app.shape("جلب الجودات")
        on_press: app.fetch_formats()

    NeonLabel:
        id: status_label
        text: app.shape("في انتظار الرابط...")
        size_hint_y: 0.3
"""

class DownloaderApp(App):
    title_text = "تطبيق تنزيل الفيديوهات"
    
    def build(self):
        self.arabic_font = ARABIC_FONT
        self.main_layout = Builder.load_string(KV_DESIGN)
        Window.softinput_mode = "below_target" # لمنع الكيبورد من تغطية حقل النص
        return self.main_layout

    def shape(self, text):
        return shape_arabic(text)

    def fetch_formats(self):
        url = self.main_layout.ids.url_input.text
        if not url:
            self.update_status("الرجاء إدخال رابط أولاً!", is_error=True)
            return
        
        self.update_status("جاري جلب الجودات المتاحة...")
        self.main_layout.ids.fetch_button.disabled = True
        threading.Thread(target=self._get_formats_thread, args=(url,)).start()

    def _get_formats_thread(self, url):
        try:
            command = ['yt-dlp', '-F', url]
            process = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
            
            formats = self._parse_formats(process.stdout)
            if not formats:
                self.update_status("لم يتم العثور على جودات متاحة أو الرابط غير صالح.", is_error=True)
                Clock.schedule_once(lambda dt: self.enable_button())
                return

            Clock.schedule_once(lambda dt: self.show_format_popup(formats, url))

        except subprocess.CalledProcessError as e:
            error_message = e.stderr.strip().split('\n')[-1]
            self.update_status(f"خطأ: {error_message}", is_error=True)
            Clock.schedule_once(lambda dt: self.enable_button())
        except Exception as e:
            self.update_status(f"خطأ غير متوقع: {e}", is_error=True)
            Clock.schedule_once(lambda dt: self.enable_button())

    def _parse_formats(self, output):
        lines = output.split('\n')
        formats = []
        start_parsing = False
        for line in lines:
            if 'ID' in line and 'EXT' in line and 'RESOLUTION' in line:
                start_parsing = True
                continue
            if start_parsing and line.strip():
                parts = line.split()
                format_id = parts[0]
                ext = parts[1]
                resolution = parts[2]
                note = ' '.join(parts[3:])
                
                # تجاهل الجودات التي تحتوي على فيديو فقط أو صوت فقط (سنقوم بدمجها لاحقاً)
                if 'video only' in note or 'audio only' in note:
                    continue

                display_text = f"{resolution} ({ext}) - {note}"
                formats.append({'id': format_id, 'text': display_text})
        return formats

    def show_format_popup(self, formats, url):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        popup_title = shape_arabic("اختر الجودة المطلوبة")
        spinner_values = [self.shape(f['text']) for f in formats]
        
        spinner = Spinner(
            text=self.shape("اختر جودة"),
            values=spinner_values,
            font_name=self.arabic_font,
            size_hint_y=None,
            height='48dp'
        )
        
        download_button = Button(text=self.shape("بدء التنزيل"), font_name=self.arabic_font, size_hint_y=None, height='48dp')
        
        content.add_widget(spinner)
        content.add_widget(download_button)
        
        popup = Popup(title=popup_title, content=content, size_hint=(0.9, 0.4), title_font=self.arabic_font)

        def start_download_action(instance):
            selected_text = spinner.text
            if selected_text == self.shape("اختر جودة"):
                return
            
            # البحث عن الـ ID المطابق للنص المختار
            selected_format_id = None
            for f in formats:
                if self.shape(f['text']) == selected_text:
                    selected_format_id = f['id']
                    break
            
            if selected_format_id:
                popup.dismiss()
                self.update_status(f"تم اختيار الجودة {selected_format_id}. بدء التنزيل...")
                threading.Thread(target=self._download_thread, args=(url, selected_format_id)).start()

        download_button.bind(on_press=start_download_action)
        popup.open()
        self.enable_button()

    def _download_thread(self, url, format_id):
        try:
            download_path = os.path.join(os.path.expanduser("~"), "Downloads")
            os.makedirs(download_path, exist_ok=True)
            
            # نستخدم format_id + أفضل صوت، ثم ندمجهم
            # هذا يضمن الحصول على أفضل جودة صوت مع الفيديو المختار
            final_format_code = f"{format_id}+bestaudio/best"

            command = [
                'yt-dlp',
                '-f', final_format_code,
                '--merge-output-format', 'mp4',
                '-o', os.path.join(download_path, '%(title)s.%(ext)s'),
                url
            ]
            
            subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
            self.update_status("اكتمل التنزيل بنجاح!")

        except subprocess.CalledProcessError as e:
            self.update_status(f"خطأ أثناء التنزيل: {e.stderr.strip().splitlines()[-1]}", is_error=True)
        except Exception as e:
            self.update_status(f"خطأ غير متوقع: {e}", is_error=True)
        finally:
            Clock.schedule_once(lambda dt: self.enable_button())

    def update_status(self, text, is_error=False):
        def update(dt):
            self.main_layout.ids.status_label.text = self.shape(text)
            self.main_layout.ids.status_label.color = (1, 0.3, 0.3, 1) if is_error else (0.7, 0.9, 1, 1)
        Clock.schedule_once(update)

    def enable_button(self):
        self.main_layout.ids.fetch_button.disabled = False

if __name__ == "__main__":
    DownloaderApp().run()
    