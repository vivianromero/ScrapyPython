from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException, NoAlertPresentException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
import requests
from PIL import Image
from io import BytesIO
import time
import json
from bs4 import BeautifulSoup

#VARIABLES

IMG_PRODUCTS_DIR = "./images/"
IMG_COLORS_DIR = "./images/colors/"
JSON_FILE = "./json_data/data.json"
NOT_AVAILABLE = "AGOTADO"
KEY_WORD = ''

class scraping_chein:
    def __ini__(self, *args):
        print('Scraping to es.shein')

    def do_click(self, object, driver):
        try:
            object.click()
        except Exception as e:
            promo = driver.find_elements_by_class_name("c-coupon-box")
            if promo:
                promo[0].find_elements_by_class_name("iconfont")[0].click()
                time.sleep(5)
                object.click()

    def llenar_detalles(self, detalles, driver, image_name, image_href):
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        print("Llenando propiedades")
        values=soup.find_all("div", "val")
        keys=soup.find_all("div", "key")
        dicc = {}
        dicc = {k.text.replace(':','').strip():v.text.strip() for k, v in zip(keys, values) if not k.text.replace(':','').strip() in dicc}
        result = {}

        color = dicc['Color'] if 'Color' in dicc else ''
        dicc['image_color_name'] = image_name
        dicc['image_color_href'] = image_href

        print("Llenando tallas")
        #tallas
        tallas = soup.find_all("div", "product-intro__size-radio")
        product_tallas = [t.text for t in tallas if not 'product-intro__size-radio_soldout' in t['class']]
        dicc['product_tallas'] = product_tallas

        print("Llenando imágenes del producto")
        #imagenes del producto
        images = driver.find_elements_by_class_name("product-intro__thumbs-item")
        names_images_600x = []

        # # se toma la url de las imagenes pequeñas que aparecen 220x293 y las de mayor
        # # tamaño tienen la misma solo se cambia 220x293por 600x
        img_prod_name = []
        img_prod_href = []

        for img in images:
            try:
                image_url_220x293 = 'https:'+ img.find_element_by_tag_name('img').get_attribute('src')
                image_name_220x293 = image_url_220x293[image_url_220x293.rfind('/')+1:]
                image_name_220x293 = image_name_220x293[:image_name_220x293.rfind('.')]
                image_url_600x = image_url_220x293.replace('220x293','600x')
                image_name, image_url = self.save_image(image_url_600x, IMG_PRODUCTS_DIR)
                img_prod_name.append(image_name)
                img_prod_href.append(image_url)
            except Exception as e:
                pass
        dicc['image_product_name'] = img_prod_name
        dicc['image_product_href'] = img_prod_href

        #tallas del producto

        if 'Color' in dicc:
            dicc.pop('Color')

        result[color]=dicc

        return result

    def save_image(self, image_url, img_dir):
        image_name = ''
        try:
            image_name = image_url[image_url.rfind('/')+1:]
            image_object = requests.get(image_url)
            if image_object.status_code == 200:
                image = Image.open(BytesIO(image_object.content))
                image.save(img_dir + image_name + "." + image.format, image.format)
                image.show()
        except Exception as e:
            pass
        return image_name, image_url

    def do_scarping(self):
        print('Iniciar una sesión del navegador')
        # Iniciar una sesión del navegador
        op = webdriver.ChromeOptions()
        op.add_argument('headless') #TODO quitar en produccion
        # user agent is really important in headless mode
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
        op.add_argument(f'user-agent={user_agent}')
        op.add_argument('disable-blink-features=AutomationControlled')
        op.add_argument('no-sandbox')
        op.add_argument('disable-dev-shm-usage')
        op.add_argument('disable-infobars')
        op.add_argument('window-size=2000,1500')
        op.add_argument("--disable-notifications")
        driver = webdriver.Chrome(options=op)

        url = "https://es.shein.com/pdsearch/"+(input_var.strip().replace(' ','%20'))
        driver.get(url)
        time.sleep(10)

        # Encuentra el tamaño de la página
        page_height = driver.execute_script("return document.body.scrollHeight")

        # Diccionario para guardar información de los productos
        dicc_productos={}

        #enlace para recorrer las paginas
        next_page = driver.find_elements_by_class_name("icons-more_right")

        cant_pages = 1
        page = 0

        if next_page:
            text = driver.find_elements_by_class_name("sui-pagination__total")[0].text
            cant_pages = int(text.split(' ')[0]) if text else 1
        cant_pages = 1
        print("====== Cargando páginas ======")
        for page in range(0, cant_pages):
            print("Página ", page+1, "de ", cant_pages)
            #haciendo scroll al final de la pagina
            for y in range(0, page_height, 500):
                driver.execute_script("window.scrollTo(0, {});".format(y))

            time.sleep(15)

            #extrayendo los productos
            products = driver.find_elements_by_class_name("S-product-item__link_jump")
            for product  in products:
                dicc_productos[product.get_attribute('data-sku')]={
                    'sku': product.get_attribute('data-sku'),
                    'description': product.text,
                    'price': product.get_attribute('data-price'),
                    'href': product.get_attribute('href')
                }

            #ir a la siguiente pagina
            if next_page:
                self.do_click(next_page[0], driver)
                time.sleep(10)

                # enlace para ir a la siguiente pagina
                next_page = driver.find_elements_by_class_name("icons-more_right")

        #Recorrer el diccionario para coger los detalles de los productos
        keys = dicc_productos.keys()
        keys = list(keys)[:3]
        list_no_disponibles = []

        cant_products = len(keys)

        if cant_products > 0:
            print("====== Obtener detalles de ", cant_products, " productos ======")
        else:
            print("!!!!!!! La búsqueda '",input_var, "' no coincide con ningún producto.")
        p=1

        for r in keys:
            print("====================================")
            print("Producto ", p, " de ", cant_products)
            #coger la url para ver los detalles del producto
            driver.get(dicc_productos[r]['href'])
            time.sleep(10)

            # parent_guid = driver.current_window_handle
            disponible = driver.find_elements_by_class_name("product-intro__add-btn")[0].text.upper()
            if disponible != NOT_AVAILABLE:
                price = driver.find_elements_by_class_name("from")[0].text.replace('€', '')
                price = price.split('\n')[price.split('\n').__len__()-1]
                dicc_productos[r]['price'] = price

                #Guia de las tallas
                print("Guía Talla del producto ",p)
                guia_talla = driver.find_elements_by_class_name('product-intro__sizeguide-head')
                dicc_guia_talla = {}
                dicc_guia_talla['Tallas'] = []
                if guia_talla:
                    self.do_click(guia_talla[0], driver)
                    time.sleep(5)
                    guia_tallas = driver.find_elements_by_class_name("common-sizetable__table")

                    if guia_tallas:
                        table = guia_tallas[0].find_element_by_xpath("//table")
                        header = [cell.text for cell in table.find_elements_by_class_name("trhead")[0].find_elements_by_xpath(".//td")]

                        row_data = []
                        rows = table.find_elements_by_class_name("common-sizetable__table-tr")[1:]
                        k = 0
                        for row in rows:
                            cells = row.find_elements_by_xpath(".//td")
                            talla = cells[0].text
                            dicc = {talla:{}}

                            i = 1
                            for cell in cells[1:]:
                                dicc[talla][header[i]] = cell.text
                                i += 1
                            dicc_guia_talla['Tallas'].append(dicc)

                dicc_productos[r]['guia_tallas'] = dicc_guia_talla['Tallas']

                print("Cargando detalles del producto ",p, " de ",cant_products)
                # se abre la tabla de los detalles del producto
                detalles = driver.find_elements_by_class_name('product-intro__description-head')
                #colores
                colors = driver.find_elements_by_class_name("product-intro__color_choose")
                img_color = ''
                dicc_detalles = {}
                image_name = ''
                image_href = ''
                cant_colors = 0
                if colors:
                    colors = colors[0].find_elements_by_class_name('product-intro__color-block')
                    cant_colors = len(colors)
                    print("Colores ", cant_colors)
                    # se recorre cada color, se da click
                    # se toman los detalles que estan en la tabla "Detalles" de la pagina con un formato llave: valor
                    # las imagen del color que se guarda con la llave 'img_color':<nombre de la imagen>
                    # las imagenes del producto para ese color que se guardan con la llave 'img_product': [nombre de las imagenes]
                    # las tallas disponibles para el color color que se guardan con la llave 'tallas': [nombre de la talla]
                    # esto se guarda en el dicc de productos con la llave 'detalles' para cada color
                    #'detalles':{<color>:{llave:valor, 'img_color':<nombre de la imagen>, 'img_product': [nombre de las imagenes],
                    # 'tallas': [nombre de la talla]}
                    c1 = 1
                    for c in colors:
                        self.do_click(c, driver)
                        time.sleep(5)
                        img_color_url = 'https:' + \
                                        c.find_elements_by_class_name('color-inner')[0].find_elements_by_xpath(".//img")[
                                            0].get_attribute('src')
                        image_name, image_href = self.save_image(img_color_url, IMG_COLORS_DIR)
                        print("Llenar detalles del color ",c1, " de ",cant_colors)
                        dicc_detalles = self.llenar_detalles(detalles, driver, image_name, image_href)
                        c1 += 1
                else:
                    print("Llenar detalles del producto ", p, " de ", cant_products)
                    dicc_detalles = self.llenar_detalles(detalles, driver, image_name, image_href)
                dicc_productos[r]['detalles'] = dicc_detalles
            else:
                print(" Producto NO DISPONIBLE")
                list_no_disponibles.append(r)
            p += 1

        if list_no_disponibles.__len__() != dicc_productos.keys().__len__() and dicc_productos.keys().__len__()>0:
            [dicc_productos.pop(key) for key in list_no_disponibles if dicc_productos]
        else:
            dicc_productos = {}

        with open(JSON_FILE, "w") as file:
            json.dump(dicc_productos, file)


        # Cerrar la sesión del navegador
        driver.quit()

        print('Scraping terminado !!!!!')

input_var = input("Buscar por: ")
myscrap = scraping_chein()
myscrap.do_scarping()
# Es importante mencionar que algunas páginas web pueden tener medidas de seguridad para evitar el scraping automatizado,
# por lo que es importante revisar los términos y condiciones de uso antes de comenzar a scrapear la página.
