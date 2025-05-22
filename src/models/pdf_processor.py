"""
PDF Processor pre konverziu PDF súborov na obrázky.
"""
import os
from pathlib import Path
from typing import List, Generator
import fitz  # PyMuPDF

from ..config import AppSettings
from ..utils.exceptions import PDFProcessingError
from ..utils.validators import validate_pdf_file
from ..utils.logging_config import get_logger


logger = get_logger(__name__)


class PDFProcessor:
    """Trieda pre spracovanie PDF súborov."""
    
    def __init__(self, settings: AppSettings):
        self.settings = settings
        logger.info(f"PDFProcessor inicializovaný s DPI: {settings.pdf_dpi}")
    
    def pdf_to_images(self, pdf_path: str, output_folder: str = None) -> List[str]:
        """
        Konvertuje PDF súbor na obrázky.
        
        Args:
            pdf_path: Cesta k PDF súboru
            output_folder: Adresár pre uloženie obrázkov (voliteľné)
            
        Returns:
            Zoznam ciest k vytvoreným obrázkom
            
        Raises:
            PDFProcessingError: Pri chybe konverzie
        """
        # Validácia PDF súboru
        validate_pdf_file(pdf_path, self.settings.max_pdf_size_mb)
        
        if output_folder is None:
            output_folder = self.settings.pdf_image_dir
        
        # Vytvorenie output adresára
        Path(output_folder).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Konvertujem PDF na obrázky: {pdf_path}")
        
        image_paths = []
        doc = None
        
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            logger.info(f"PDF má {total_pages} strán")
            
            for page_num in range(total_pages):
                try:
                    page = doc.load_page(page_num)
                    
                    # Vytvorenie obrázka s nastaveným DPI
                    pix = page.get_pixmap(dpi=self.settings.pdf_dpi)
                    
                    # Generovanie názvu súboru
                    image_filename = f"page_{page_num + 1}.png"
                    image_path = os.path.join(output_folder, image_filename)
                    
                    # Uloženie obrázka
                    pix.save(image_path)
                    image_paths.append(image_path)
                    
                    logger.debug(f"Vytvorený obrázok: {image_path}")
                    
                except Exception as e:
                    logger.error(f"Chyba pri konverzii strany {page_num + 1}: {e}")
                    raise PDFProcessingError(f"Chyba pri konverzii strany {page_num + 1}: {e}")
            
            logger.info(f"Úspešne konvertovaných {len(image_paths)} strán z PDF")
            return image_paths
            
        except Exception as e:
            logger.error(f"Chyba pri konverzii PDF {pdf_path}: {e}")
            raise PDFProcessingError(f"Chyba pri konverzii PDF: {e}")
        
        finally:
            if doc:
                doc.close()
    
    def pdf_to_images_generator(self, pdf_path: str, output_folder: str = None) -> Generator[tuple, None, None]:
        """
        Generátor pre konverziu PDF na obrázky - memory efficient.
        
        Args:
            pdf_path: Cesta k PDF súboru
            output_folder: Adresár pre uloženie obrázkov
            
        Yields:
            Tuple (page_number, image_path)
            
        Raises:
            PDFProcessingError: Pri chybe konverzie
        """
        validate_pdf_file(pdf_path, self.settings.max_pdf_size_mb)
        
        if output_folder is None:
            output_folder = self.settings.pdf_image_dir
        
        Path(output_folder).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Generujem obrázky z PDF: {pdf_path}")
        
        doc = None
        
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            logger.info(f"PDF má {total_pages} strán (generator mode)")
            
            for page_num in range(total_pages):
                try:
                    page = doc.load_page(page_num)
                    pix = page.get_pixmap(dpi=self.settings.pdf_dpi)
                    
                    image_filename = f"page_{page_num + 1}.png"
                    image_path = os.path.join(output_folder, image_filename)
                    
                    pix.save(image_path)
                    
                    logger.debug(f"Generovaný obrázok: {image_path}")
                    yield (page_num + 1, image_path)
                    
                except Exception as e:
                    logger.error(f"Chyba pri generovaní strany {page_num + 1}: {e}")
                    raise PDFProcessingError(f"Chyba pri generovaní strany {page_num + 1}: {e}")
        
        except Exception as e:
            logger.error(f"Chyba pri generovaní z PDF {pdf_path}: {e}")
            raise PDFProcessingError(f"Chyba pri generovaní z PDF: {e}")
        
        finally:
            if doc:
                doc.close()
    
    def get_pdf_info(self, pdf_path: str) -> dict:
        """
        Vráti informácie o PDF súbore.
        
        Args:
            pdf_path: Cesta k PDF súboru
            
        Returns:
            Slovník s informáciami o PDF
            
        Raises:
            PDFProcessingError: Pri chybe čítania PDF
        """
        validate_pdf_file(pdf_path, self.settings.max_pdf_size_mb)
        
        doc = None
        
        try:
            doc = fitz.open(pdf_path)
            
            info = {
                "filename": os.path.basename(pdf_path),
                "page_count": len(doc),
                "file_size_mb": os.path.getsize(pdf_path) / (1024 * 1024),
                "metadata": doc.metadata,
                "is_encrypted": doc.is_encrypted,
                "can_modify": not doc.is_encrypted or doc.authenticate(""),
            }
            
            logger.info(f"PDF info pre {pdf_path}: {info['page_count']} strán, {info['file_size_mb']:.2f}MB")
            return info
            
        except Exception as e:
            logger.error(f"Chyba pri čítaní PDF info pre {pdf_path}: {e}")
            raise PDFProcessingError(f"Chyba pri čítaní PDF info: {e}")
        
        finally:
            if doc:
                doc.close()
    
    def cleanup_images(self, image_paths: List[str]) -> None:
        """
        Vymaže dočasné obrázky.
        
        Args:
            image_paths: Zoznam ciest k obrázkom na vymazanie
        """
        logger.info(f"Čistím {len(image_paths)} dočasných obrázkov")
        
        for image_path in image_paths:
            try:
                if os.path.exists(image_path):
                    os.remove(image_path)
                    logger.debug(f"Vymazaný obrázok: {image_path}")
            except OSError as e:
                logger.warning(f"Nepodarilo sa vymazať obrázok {image_path}: {e}")
        
        logger.info("Čistenie obrázkov dokončené")
    
    def get_available_pdfs(self, directory: str = None) -> List[str]:
        """
        Vráti zoznam dostupných PDF súborov v adresári.
        
        Args:
            directory: Adresár na prehľadanie (voliteľné)
            
        Returns:
            Zoznam názvov PDF súborov
        """
        if directory is None:
            directory = self.settings.input_pdf_dir
        
        if not os.path.exists(directory):
            logger.warning(f"Adresár neexistuje: {directory}")
            return []
        
        pdf_files = []
        
        for filename in os.listdir(directory):
            if filename.lower().endswith('.pdf'):
                pdf_path = os.path.join(directory, filename)
                if os.path.isfile(pdf_path):
                    pdf_files.append(filename)
        
        logger.info(f"Nájdených {len(pdf_files)} PDF súborov v {directory}")
        return sorted(pdf_files) 