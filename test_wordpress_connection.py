import logging
from app.config import WORDPRESS_CONFIG, WORDPRESS_CATEGORIES
from app.wordpress import WordPressClient
import time

# Configure logging to see the output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """
    Initializes the WordPress client and runs the category creation test.
    """
    logger = logging.getLogger(__name__)
    logger.info("Inicializando o cliente WordPress para o teste...")
    
    try:
        wp_client = WordPressClient(config=WORDPRESS_CONFIG, categories_map=WORDPRESS_CATEGORIES)
        
        logger.info("Cliente WordPress inicializado. Executando o teste de criação de categoria...")
        success, message = wp_client.test_category_creation()
        
        print("\n" + "="*50)
        if success:
            print("✅ Resultado do Teste: SUCESSO")
        else:
            print("❌ Resultado do Teste: FALHA")
        print(f"Mensagem: {message}")
        print("="*50 + "\n")

    except Exception as e:
        logger.error(f"Erro crítico durante a inicialização do cliente ou teste: {e}", exc_info=True)
        print("\n" + "="*50)
        print("❌ Resultado do Teste: FALHA CRÍTICA")
        print(f"Mensagem: Ocorreu um erro grave. Verifique os logs acima para detalhes.")
        print("="*50 + "\n")

if __name__ == "__main__":
    main()
