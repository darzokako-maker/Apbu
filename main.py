
import sys
import subprocess
import threading
import re
import customtkinter as ctk
import google.generativeai as genai
import yaml

# Gemini API goldawyny sazlamak
# Bu ýerde ulanyjynyň beren API açary ulanylýar
API_KEY = "AIzaSyB5raQLHJ5ipMw6qm7boa8cPkxZMyPDNyw"
genai.configure(api_key=API_KEY)

# Interfeýsiň reňk we tema sazlamalary
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AICodeStudio(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("AI Code Studio - Python & YAML")
        self.geometry("1200x750")

        # --- ÝOKARKY MENÝU PANELI ---
        self.menu_bar = ctk.CTkFrame(self, height=50, corner_radius=0)
        self.menu_bar.pack(side="top", fill="x")

        # Rejim saýlaýjy (Python ýa-da YAML)
        self.mode_label = ctk.CTkLabel(self.menu_bar, text="Rejim:", font=("Segoe UI", 12, "bold"))
        self.mode_label.pack(side="left", padx=(15, 5), pady=10)

        self.mode_selector = ctk.CTkComboBox(
            self.menu_bar, 
            values=["Python", "YAML"], 
            command=self.on_mode_change,
            width=100
        )
        self.mode_selector.set("Python")
        self.mode_selector.pack(side="left", padx=5, pady=10)

        # Düwmeler
        self.run_btn = ctk.CTkButton(
            self.menu_bar, 
            text="▶ Kody işlet / Barlamak", 
            width=180, 
            fg_color="#2ea44f", 
            hover_color="#22863a", 
            command=self.execute_action
        )
        self.run_btn.pack(side="left", padx=15, pady=10)

        self.clear_btn = ctk.CTkButton(
            self.menu_bar, 
            text="Arassala", 
            width=100, 
            fg_color="#444", 
            hover_color="#555", 
            command=self.clear_editor
        )
        self.clear_btn.pack(side="left", padx=5, pady=10)

        # --- ESASY IŞ MEÝDANY ---
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(side="top", fill="both", expand=True, padx=10, pady=5)

        # Çep panel: Kod redaktory we Terminal
        self.left_panel = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.left_panel.pack(side="left", fill="both", expand=True, padx=(0, 5))

        self.editor_title = ctk.CTkLabel(self.left_panel, text="Kod redaktory (main.py)", font=("Segoe UI", 12, "bold"))
        self.editor_title.pack(anchor="w", pady=2)

        # Kod ýazylýan tekst meýdançasy
        self.code_editor = ctk.CTkTextbox(self.left_panel, font=("Consolas", 14), undo=True, wrap="none")
        self.code_editor.pack(fill="both", expand=True)
        
        # Real wagtda sözdizimi renklendirmesini (Syntax Highlighting) işe girizmek
        self.code_editor.bind("<KeyRelease>", self.trigger_highlighting)
        
        # Başlangyç tekst
        self.set_default_code("Python")

        # Aşaky panel: Terminal / Çykysy
        self.terminal_title = ctk.CTkLabel(self.left_panel, text="Terminal çykysy", font=("Segoe UI", 12, "bold"))
        self.terminal_title.pack(anchor="w", pady=(10, 2))

        self.terminal_output = ctk.CTkTextbox(self.left_panel, height=180, font=("Consolas", 12), fg_color="#121212", text_color="#00ff00")
        self.terminal_output.pack(fill="x")
        self.terminal_output.configure(state="disabled")

        # Sag panel: AI Kömekçi bölümi
        self.right_panel = ctk.CTkFrame(self.main_container, width=380, fg_color="#1e1e1e")
        self.right_panel.pack(side="right", fill="both", padx=(5, 0))
        self.right_panel.pack_propagate(False)

        self.ai_title = ctk.CTkLabel(self.right_panel, text="🤖 Gemini AI Kömekçisi", font=("Segoe UI", 14, "bold"), text_color="#3b82f6")
        self.ai_title.pack(pady=10)

        self.ai_chat_view = ctk.CTkTextbox(self.right_panel, font=("Segoe UI", 12), wrap="word")
        self.ai_chat_view.pack(fill="both", expand=True, padx=10, pady=5)
        self.ai_chat_view.insert("1.0", "AI: Salam! Men Gemini AI kömekçisi. Kodyňyzy barlap bilýärin, ýalňyşlyklary düzedip bilýärin ýa-da täze funksiýalar goşup bilýärin. Soragyňyzy ýazyň!\n\n")
        self.ai_chat_view.configure(state="disabled")

        self.ai_input = ctk.CTkEntry(self.right_panel, placeholder_text="AI-dan soraň (mysal: Kody optimizirle)...")
        self.ai_input.pack(fill="x", padx=10, pady=5)
        self.ai_input.bind("<Return>", lambda event: self.ask_gemini())

        self.ai_send_btn = ctk.CTkButton(self.right_panel, text="Sora / Kody ibermek", command=self.ask_gemini)
        self.ai_send_btn.pack(fill="x", padx=10, pady=(0, 15))

        # Sözdizimi renklendirme reňklerini kesgitlemek
        self.setup_highlight_tags()

    def setup_highlight_tags(self):
        """ Redaktor üçin reňkleri we tegleri sazlaýar """
        # Tekst widjetine gönüden-göni elýeterlilik gazanmak
        self.txt = self.code_editor._textbox
        self.txt.tag_config("keyword", foreground="#ff79c6") # Python açar sözleri
        self.txt.tag_config("string", foreground="#f1fa8c")  # Setirler
        self.txt.tag_config("comment", foreground="#6272a4") # Teswirler
        self.txt.tag_config("number", foreground="#bd93f9")  # Sanlar
        self.txt.tag_config("yaml_key", foreground="#8be9fd") # YAML açarlary

    def trigger_highlighting(self, event=None):
        """ Tekst ýazylanda degişli reňkleri awtomatiki ulanýar """
        # Öňki tegleri aýyrmak
        for tag in ["keyword", "string", "comment", "number", "yaml_key"]:
            self.txt.tag_remove(tag, "1.0", "end")

        content = self.code_editor.get("1.0", "end-1c")
        current_mode = self.mode_selector.get()

        if current_mode == "Python":
            # Python açar sözleri
            keywords = r"\b(def|class|import|from|return|if|else|elif|for|while|in|print|try|except|as|with|pass|lambda)\b"
            for match in re.finditer(keywords, content):
                start = f"1.0 + {match.start()} chars"
                end = f"1.0 + {match.end()} chars"
                self.txt.tag_add("keyword", start, end)

            # Sanlar
            for match in re.finditer(r"\b\d+\b", content):
                start = f"1.0 + {match.start()} chars"
                end = f"1.0 + {match.end()} chars"
                self.txt.tag_add("number", start, end)

            # Setirler
            for match in re.finditer(r"(\".*?\"|'.*?')", content):
                start = f"1.0 + {match.start()} chars"
                end = f"1.0 + {match.end()} chars"
                self.txt.tag_add("string", start, end)

            # Teswirler (#)
            for match in re.finditer(r"#.*", content):
                start = f"1.0 + {match.start()} chars"
                end = f"1.0 + {match.end()} chars"
                self.txt.tag_add("comment", start, end)

        elif current_mode == "YAML":
            # YAML açarlary (mysal: açar: )
            for match in re.finditer(r"^\s*[\w\-\d_]+(?=\s*:)", content, flags=re.MULTILINE):
                start = f"1.0 + {match.start()} chars"
                end = f"1.0 + {match.end()} chars"
                self.txt.tag_add("yaml_key", start, end)

            # Sanlar we logiki bahalar
            for match in re.finditer(r"\b(true|false|null|\d+)\b", content, flags=re.IGNORECASE):
                start = f"1.0 + {match.start()} chars"
                end = f"1.0 + {match.end()} chars"
                self.txt.tag_add("number", start, end)

            # Setirler (dyrnak içindäkiler)
            for match in re.finditer(r"(\".*?\"|'.*?')", content):
                start = f"1.0 + {match.start()} chars"
                end = f"1.0 + {match.end()} chars"
                self.txt.tag_add("string", start, end)

            # Teswirler
            for match in re.finditer(r"#.*", content):
                start = f"1.0 + {match.start()} chars"
                end = f"1.0 + {match.end()} chars"
                self.txt.tag_add("comment", start, end)

    def on_mode_change(self, selected_mode):
        """ Rejim çalşanynda degişli başlangyç kody goýýar """
        self.editor_title.configure(text=f"Kod redaktory ({'main.py' if selected_mode == 'Python' else 'config.yml'})")
        self.set_default_code(selected_mode)
        self.trigger_highlighting()

    def set_default_code(self, mode):
        """ Redaktora deslapky şablonlary ýerleşdirýär """
        self.code_editor.delete("1.0", ctk.END)
        if mode == "Python":
            template = (
                "# Python Şablony\n"
                "def salamlas():\n"
                "    print('Salam Dünýä!')\n\n"
                "salamlas()\n"
            )
        else:
            template = (
                "# YAML Konfigurasiýa Şablony\n"
                "serwer:\n"
                "  port: 8080\n"
                "  host: \"localhost\"\n"
                "  is_active: true\n\n"
                "maglumatlar_bazasy:\n"
                "  user: \"admin\"\n"
                "  pass: \"secret_key_123\"\n"
            )
        self.code_editor.insert("1.0", template)

    def execute_action(self):
        """ Saýlanan rejime görä kody başladýar ýa-da YAML barlaýar """
        current_mode = self.mode_selector.get()
        code = self.code_editor.get("1.0", ctk.END)

        self.terminal_output.configure(state="normal")
        self.terminal_output.delete("1.0", ctk.END)
        self.terminal_output.insert("1.0", f"{current_mode} işlenilýär...\n" + "-"*40 + "\n")
        self.terminal_output.configure(state="disabled")

        if current_mode == "Python":
            # Python koduny aýratyn thread-de işletmek
            def run():
                try:
                    proc = subprocess.Popen(
                        [sys.executable, "-c", code],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    stdout, stderr = proc.communicate()
                    self.write_to_terminal(stdout, stderr)
                except Exception as e:
                    self.write_to_terminal("", f"Ulgam hatasy: {str(e)}")

            threading.Thread(target=run).start()

        elif current_mode == "YAML":
            # YAML barlagyny amala aşyrmak
            try:
                parsed_yaml = yaml.safe_load(code)
                success_msg = f"✓ YAML üstünlikli barlanyldy!\n\nOkalan maglumat:\n{parsed_yaml}"
                self.write_to_terminal(success_msg, "")
            except Exception as e:
                self.write_to_terminal("", f"✗ YAML Ýalňyşlygy:\n{str(e)}")

    def write_to_terminal(self, out, err):
        """ Terminala maglumat ýazdyrýar """
        self.terminal_output.configure(state="normal")
        if out:
            self.terminal_output.insert(ctk.END, out)
        if err:
            self.terminal_output.insert(ctk.END, f"\nÝALŇYŞLYK:\n{err}")
        self.terminal_output.configure(state="disabled")

    def ask_gemini(self):
        """ Gemini AI modeline sowal we kod ugradýar """
        user_prompt = self.ai_input.get()
        if not user_prompt:
            return

        current_code = self.code_editor.get("1.0", ctk.END)
        current_mode = self.mode_selector.get()

        self.ai_chat_view.configure(state="normal")
        self.ai_chat_view.insert(ctk.END, f"\nSiz: {user_prompt}\n")
        self.ai_chat_view.configure(state="disabled")
        self.ai_input.delete(0, ctk.END)

        def call_api():
            try:
                # Gemini modelini çagyrmak
                model = genai.GenerativeModel("gemini-1.5-flash")
                
                # AI-a gowy kontekst bermek
                prompt_context = (
                    f"Sen professional programma üpjünçiligi hünärmeni. "
                    f"Ulanýan dilimiz we formatymyz: {current_mode}.\n\n"
                    f"Häzirki ýazylan kod:\n```{current_mode}\n{current_code}```\n\n"
                    f"Ulanyjynyň soragy: {user_prompt}\n\n"
                    f"Haýyş, jogaby gysga, düşnükli we anyk mysallar bilen ber."
                )
                
                response = model.generate_content(prompt_context)
                ai_response = response.text
            except Exception as e:
                ai_response = f"API Hatasy döredi! Sazlamalary ýa-da internet birikmesini barlaň. Hata: {str(e)}"

            self.ai_chat_view.configure(state="normal")
            self.ai_chat_view.insert(ctk.END, f"\nGemini AI: {ai_response}\n")
            self.ai_chat_view.see(ctk.END)
            self.ai_chat_view.configure(state="disabled")

        threading.Thread(target=call_api).start()

    def clear_editor(self):
        """ Redaktory we terminaly arassalaýar """
        self.code_editor.delete("1.0", ctk.END)
        self.terminal_output.configure(state="normal")
        self.terminal_output.delete("1.0", ctk.END)
        self.terminal_output.configure(state="disabled")

if __name__ == "__main__":
    app = AICodeStudio()
    app.mainloop()

```
      
