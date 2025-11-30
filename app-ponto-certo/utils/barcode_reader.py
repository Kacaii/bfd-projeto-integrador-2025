import cv2
import threading
from typing import Callable, Optional
import time


class BarcodeReader:
    def __init__(self):
        self.is_running = False
        self.thread = None
        self.on_barcode_detected: Optional[Callable[[str], None]] = None
        self.cap = None

    def start_camera(self, on_barcode_detected: Callable[[str], None]):
        """Inicia a câmera em uma thread separada"""
        if self.is_running:
            print("⚠️ Câmera já está em execução")
            return

        self.on_barcode_detected = on_barcode_detected
        self.is_running = True
        self.thread = threading.Thread(target=self._camera_loop, daemon=True)
        self.thread.start()
        print("📷 Thread da câmera iniciada")

    def _camera_loop(self):
        """Loop principal da câmera"""
        try:
            print("🔍 Abrindo câmera (index=0)...")
            self.cap = cv2.VideoCapture(0)

            # Esperar um pouco para câmera inicializar
            time.sleep(0.5)

            if not self.cap.isOpened():
                print("❌ Erro: Não foi possível abrir a câmera (index=0)")
                print(
                    "💡 Dica: Verifique se a câmera está conectada e em uso por outro programa"
                )
                self.is_running = False
                return

            print("✅ Câmera aberta com sucesso!")
            print("🔍 Apontando a câmera para o código de barras...")
            frame_count = 0
            pyzbar_error = False

            # Importar pyzbar uma vez no início
            try:
                from pyzbar.pyzbar import decode
            except ImportError as e:
                print(f"❌ Erro ao importar pyzbar: {e}")
                print("💡 Execute: poetry add pyzbar")
                pyzbar_error = True

            while self.is_running:
                ret, frame = self.cap.read()
                if not ret:
                    print("❌ Erro ao ler frame da câmera")
                    break

                frame_count += 1

                # Decodificar usando pyzbar
                if not pyzbar_error:
                    try:
                        # Converter para escala de cinza para melhor detecção
                        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                        # Aumentar contraste usando CLAHE
                        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                        adjusted_frame = clahe.apply(gray_frame)

                        barcodes = decode(adjusted_frame)

                        if barcodes:
                            for barcode in barcodes:
                                barcode_data = barcode.data.decode("utf-8")
                                print(f"✅ Código detectado: {barcode_data}")
                                if self.on_barcode_detected:
                                    self.on_barcode_detected(barcode_data)
                                # Sair após detectar o primeiro código
                                self.stop_camera()
                                return
                        elif frame_count % 30 == 0:
                            print(f"🔄 Procurando código... (frames: {frame_count})")

                    except Exception as e:
                        if frame_count == 1:
                            print(f"⚠️ Erro ao decodificar: {e}")
                            print("💡 Verifique se o código está bem posicionado")

            self.stop_camera()

        except Exception as e:
            print(f"❌ Erro ao ler câmera: {e}")
        finally:
            if self.cap:
                self.cap.release()
            cv2.destroyAllWindows()
            self.is_running = False
            print("🛑 Câmera finalizada")

    def stop_camera(self):
        """Para a câmera"""
        print("🛑 Parando câmera...")
        self.is_running = False
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()

    def is_camera_available(self) -> bool:
        """Verifica se a câmera está disponível"""
        try:
            print("🔍 Verificando disponibilidade da câmera...")
            cap = cv2.VideoCapture(0)
            time.sleep(0.3)
            if cap.isOpened():
                cap.release()
                print("✅ Câmera disponível!")
                return True
            else:
                print("❌ Câmera não abriu (pode estar em uso ou desconectada)")
                return False
        except Exception as e:
            print(f"❌ Erro ao verificar câmera: {e}")
            return False
