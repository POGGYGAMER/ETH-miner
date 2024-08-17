import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.clock import Clock
from threading import Thread, Event
import secrets
from mnemonic import Mnemonic
from web3 import Web3
from eth_account import Account
import logging
import os

# Enable unaudited HD wallet features
Account.enable_unaudited_hdwallet_features()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Replace with your own Infura URL or other Ethereum provider URL
INFURA_URL = os.getenv('INFURA_URL', 'https://mainnet.infura.io/v3/12133e1121d145538edf9384094f7f2d')

class EthereumAddressFinderApp(App):
    def build(self):
        self.stop_event = Event()
        self.thread = None
        self.saved_phrases = []  # List to store saved phrases
        self.generated_count = 0  # Counter for generated phrases

        self.root = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Create text areas
        self.result_box = TextInput(readonly=True, background_color=(0.18, 0.18, 0.18, 1), foreground_color=(1, 1, 1, 1))
        self.result_scroll = ScrollView(size_hint=(1, 0.7))
        self.result_scroll.add_widget(self.result_box)
        
        self.status_box = TextInput(readonly=True, size_hint=(1, 0.1), background_color=(1, 0.75, 0.07, 1), foreground_color=(0, 0, 0, 1), font_size='18sp')
        
        self.root.add_widget(self.result_scroll)
        self.root.add_widget(self.status_box)
        
        # Create a label to display the number of generated phrases
        self.counter_label = Label(text=f"Phrases Generated: {self.generated_count}", size_hint=(1, 0.1), font_size='16sp')
        self.root.add_widget(self.counter_label)

        # Create buttons
        self.button_layout = BoxLayout(size_hint=(1, 0.2), spacing=10)
        
        self.start_button = Button(text="Start", background_color=(0.3, 0.7, 0.3, 1), on_press=self.start)
        self.stop_button = Button(text="Stop", background_color=(0.9, 0.3, 0.3, 1), on_press=self.stop)
        self.restart_button = Button(text="Restart", background_color=(0.2, 0.6, 1, 1), on_press=self.restart)
        self.save_button = Button(text="Save", background_color=(1, 0.76, 0.07, 1), on_press=self.save_phrases)
        
        self.button_layout.add_widget(self.start_button)
        self.button_layout.add_widget(self.stop_button)
        self.button_layout.add_widget(self.restart_button)
        self.button_layout.add_widget(self.save_button)
        
        self.root.add_widget(self.button_layout)
        
        return self.root

    def generate_mnemonic(self):
        mnemo = Mnemonic("english")
        return mnemo.generate()
    
    def mnemonic_to_address(self, mnemonic_phrase):
        try:
            account = Account.from_mnemonic(mnemonic_phrase)
            return account.address
        except Exception as e:
            logger.error(f"Error converting mnemonic to address: {e}")
            return None
    
    def check_balance(self, address):
        try:
            web3 = Web3(Web3.HTTPProvider(INFURA_URL))
            balance = web3.eth.get_balance(address)
            return Web3.from_wei(balance, 'ether')
        except Exception as e:
            logger.error(f"Error checking balance: {e}")
            return 0
    
    def update_ui(self, message, status=None):
        # Schedule the update of the UI on the main thread
        Clock.schedule_once(lambda dt: self._update_ui_thread_safe(message, status))
    
    def _update_ui_thread_safe(self, message, status):
        self.result_box.text += message + '\n'  # Add extra newline for vertical space
        if status is not None:
            self.status_box.text = status
    
    def update_counter(self):
        # Use a function instead of direct assignment in the lambda
        def update_label(dt):
            self.counter_label.text = f"Phrases Generated: {self.generated_count}"
        Clock.schedule_once(update_label)

    def find_balance(self):
        while not self.stop_event.is_set():
            self.generated_count += 1
            self.update_counter()  # Update the counter label
            mnemonic_phrase = self.generate_mnemonic()
            address = self.mnemonic_to_address(mnemonic_phrase)
            if not address:
                continue
            balance = self.check_balance(address)
            
            result_text = (f"Mnemonic: {mnemonic_phrase}\n"
                           f"Address: {address}\n"
                           f"Balance: {balance} ETH\n"
                           f"Total Phrases Generated: {self.generated_count}\n")
            self.update_ui(result_text)
            
            if balance > 0:
                self.update_ui("Wallet Found!", "Wallet Found!")
                self.saved_phrases.append(mnemonic_phrase)
                break
            else:
                self.update_ui("No balance. Generating a new mnemonic...\n")
    
    def start(self, instance):
        if not self.thread or not self.thread.is_alive():
            self.stop_event.clear()
            self.thread = Thread(target=self.find_balance)
            self.thread.start()
            self.update_ui("", "Searching...")
    
    def stop(self, instance):
        if self.thread and self.thread.is_alive():
            self.stop_event.set()
            self.thread.join()
        self.update_ui("Stopped")
    
    def restart(self, instance):
        self.stop(None)
        self.result_box.text = ''
        self.start(None)

    def save_phrases(self, instance):
        if not self.saved_phrases:
            self.update_ui("No phrases to save.\n")
            return
        
        content = FileChooserListView()
        popup = Popup(title="Save Phrases", content=content, size_hint=(0.9, 0.9))
        
        def on_selection(instance, selection):
            if selection:
                file_path = selection[0]
                try:
                    with open(file_path, 'w') as file:
                        for phrase in self.saved_phrases:
                            file.write(f"{phrase}\n")
                    self.update_ui("Phrases saved successfully.\n")
                    self.saved_phrases.clear()
                except Exception as e:
                    logger.error(f"Error saving phrases: {e}")
            popup.dismiss()
        
        content.bind(on_submit=on_selection)
        popup.open()

if __name__ == '__main__':
    EthereumAddressFinderApp().run()