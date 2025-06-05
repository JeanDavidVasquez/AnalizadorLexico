import xml.etree.ElementTree as ET
import re

class AFD:
    def __init__(self, jff_path):
        self.estados_data = {}
        self.transiciones = {}
        self.estado_inicial = None
        self.estados_finales = set()
        self._cargar_desde_jff(jff_path)

    def _cargar_desde_jff(self, jff_path):
        tree = ET.parse(jff_path)
        root = tree.getroot()
        temp_estados_por_id = {}

        automaton_node = root.find("automaton")
        if automaton_node is None:
            automaton_node = root

        for state_node in automaton_node.iter("state"):
            state_id = state_node.get("id")
            state_name = state_node.get("name")
            label_node = state_node.find("label")
            label_text = state_name
            if label_node is not None and label_node.text is not None:
                label_text = label_node.text

            temp_estados_por_id[state_id] = state_name
            self.estados_data[state_name] = {'label': label_text}

            if state_node.find("initial") is not None:
                self.estado_inicial = state_name
            if state_node.find("final") is not None:
                self.estados_finales.add(state_name)

        for trans_node in automaton_node.iter("transition"):
            from_id = trans_node.find("from").text
            to_id = trans_node.find("to").text
            simbolo_read_element = trans_node.find("read")
            simbolo = simbolo_read_element.text if simbolo_read_element is not None and simbolo_read_element.text is not None else ""

            desde = temp_estados_por_id.get(from_id)
            hacia = temp_estados_por_id.get(to_id)

            if desde and hacia:
                for s_expandido in self.expandir_rango(simbolo):
                    clave_transicion = (desde, s_expandido)
                    if clave_transicion not in self.transiciones:
                        self.transiciones[clave_transicion] = set()
                    self.transiciones[clave_transicion].add(hacia)

    def expandir_rango(self, simbolo):
        if not simbolo:
            return [""]

        if re.fullmatch(r"\[[a-z]-[a-z]\]", simbolo) and len(simbolo) == 5:
            inicio, fin = simbolo[1], simbolo[3]
            return [chr(c) for c in range(ord(inicio), ord(fin) + 1)]
        elif re.fullmatch(r"\[[0-9]-[0-9]\]", simbolo) and len(simbolo) == 5:
            inicio, fin = simbolo[1], simbolo[3]
            return [str(c) for c in range(int(inicio), int(fin) + 1)]
        elif re.fullmatch(r"\[[A-Z]-[A-Z]\]", simbolo) and len(simbolo) == 5:
            inicio, fin = simbolo[1], simbolo[3]
            return [chr(c) for c in range(ord(inicio), ord(fin) + 1)]
        else:
            return [simbolo]

    def _calcular_clausura_epsilon_para_conjunto(self, conjunto_estados_inicial):
        if not conjunto_estados_inicial:
            return set()

        clausura = set(conjunto_estados_inicial)
        pila = list(conjunto_estados_inicial)

        while pila:
            estado_actual = pila.pop()
            clave_epsilon = (estado_actual, "")

            if clave_epsilon in self.transiciones:
                for estado_siguiente_epsilon in self.transiciones[clave_epsilon]:
                    if estado_siguiente_epsilon not in clausura:
                        clausura.add(estado_siguiente_epsilon)
                        pila.append(estado_siguiente_epsilon)
        return clausura

    def _puede_formar_token_completo_desde_posicion(self, linea, posicion):
        """
        Verifica si desde una posición específica se puede formar un token completo y válido
        """
        if posicion >= len(linea):
            return False
        
        # Intentar reconocer un token completo desde esta posición
        lexema, _, _ = self._simular_nfa_epsilon_para_token_simple(linea, posicion)
        return lexema is not None

    def _simular_nfa_epsilon_para_token_simple(self, linea, inicio_indice):
        """
        Versión simplificada que no verifica tokens pegados (para evitar recursión)
        """
        conjunto_estados_activos = self._calcular_clausura_epsilon_para_conjunto({self.estado_inicial})

        acumulador = ""
        mejor_concordancia_encontrada = (None, None, inicio_indice)

        for i in range(inicio_indice, len(linea)):
            simbolo_actual = linea[i]

            conjunto_estados_despues_simbolo = set()
            for estado_q in conjunto_estados_activos:
                clave_transicion = (estado_q, simbolo_actual)
                if clave_transicion in self.transiciones:
                    conjunto_estados_despues_simbolo.update(self.transiciones[clave_transicion])

            if not conjunto_estados_despues_simbolo:
                break

            conjunto_estados_activos = self._calcular_clausura_epsilon_para_conjunto(conjunto_estados_despues_simbolo)

            if not conjunto_estados_activos:
                break

            acumulador += simbolo_actual

            estados_finales_alcanzados = conjunto_estados_activos.intersection(self.estados_finales)
            if estados_finales_alcanzados:
                un_estado_final_representativo = list(estados_finales_alcanzados)[0]
                mejor_concordancia_encontrada = (acumulador, un_estado_final_representativo, i + 1)

        palabra_reconocida, nombre_estado_final, indice_siguiente_char = mejor_concordancia_encontrada

        if palabra_reconocida is not None:
            if nombre_estado_final in self.estados_data:
                etiqueta = self.estados_data[nombre_estado_final]['label']
                return palabra_reconocida, etiqueta, indice_siguiente_char
            else:
                return palabra_reconocida, "ETIQUETA_DESCONOCIDA_EN_ESTADO_FINAL", indice_siguiente_char
        else:
            return None, None, inicio_indice

    def _simular_nfa_epsilon_para_token(self, linea, inicio_indice):
        conjunto_estados_activos = self._calcular_clausura_epsilon_para_conjunto({self.estado_inicial})

        acumulador = ""
        mejor_concordancia_encontrada = (None, None, inicio_indice)

        for i in range(inicio_indice, len(linea)):
            simbolo_actual = linea[i]

            conjunto_estados_despues_simbolo = set()
            for estado_q in conjunto_estados_activos:
                clave_transicion = (estado_q, simbolo_actual)
                if clave_transicion in self.transiciones:
                    conjunto_estados_despues_simbolo.update(self.transiciones[clave_transicion])

            if not conjunto_estados_despues_simbolo:
                break

            conjunto_estados_activos = self._calcular_clausura_epsilon_para_conjunto(conjunto_estados_despues_simbolo)

            if not conjunto_estados_activos:
                break

            acumulador += simbolo_actual

            estados_finales_alcanzados = conjunto_estados_activos.intersection(self.estados_finales)
            if estados_finales_alcanzados:
                un_estado_final_representativo = list(estados_finales_alcanzados)[0]
                mejor_concordancia_encontrada = (acumulador, un_estado_final_representativo, i + 1)

        palabra_reconocida, nombre_estado_final, indice_siguiente_char = mejor_concordancia_encontrada

        if palabra_reconocida is not None:
            # Verificar si hay caracteres pegados que forman otro token válido
            # (esto indica que los tokens deberían estar separados por espacios)
            if (indice_siguiente_char < len(linea) and 
                not linea[indice_siguiente_char].isspace() and
                self._puede_formar_token_completo_desde_posicion(linea, indice_siguiente_char)):
                # Si hay otro token válido pegado, rechazar este token
                return None, None, inicio_indice
            
            if nombre_estado_final in self.estados_data:
                etiqueta = self.estados_data[nombre_estado_final]['label']
                return palabra_reconocida, etiqueta, indice_siguiente_char
            else:
                return palabra_reconocida, "ETIQUETA_DESCONOCIDA_EN_ESTADO_FINAL", indice_siguiente_char
        else:
            return None, None, inicio_indice

    def _consumir_token_invalido(self, linea, inicio):
        """
        Consume caracteres hasta encontrar un espacio en blanco
        """
        i = inicio
        token_invalido = ""
        
        while i < len(linea) and not linea[i].isspace():
            token_invalido += linea[i]
            i += 1
        
        return token_invalido, i

    def _es_secuencia_completa_valida(self, linea, inicio):
        """
        Verifica si toda la secuencia sin espacios desde la posición es válida como un solo token
        o como múltiples tokens válidos separables
        """
        # Encontrar el final de la secuencia (hasta el próximo espacio)
        fin = inicio
        while fin < len(linea) and not linea[fin].isspace():
            fin += 1
        
        secuencia_completa = linea[inicio:fin]
        
        # Intentar reconocer la secuencia completa como un solo token
        lexema, _, _ = self._simular_nfa_epsilon_para_token_simple(secuencia_completa, 0)
        if lexema == secuencia_completa:
            return True, [lexema]
        
        # Si no es un solo token válido, verificar si son múltiples tokens válidos
        tokens_encontrados = []
        pos = 0
        
        while pos < len(secuencia_completa):
            lexema, _, nueva_pos = self._simular_nfa_epsilon_para_token_simple(secuencia_completa, pos)
            if lexema is None:
                # No se pudo reconocer un token válido desde esta posición
                return False, []
            
            tokens_encontrados.append(lexema)
            pos = nueva_pos
        
        # Si llegamos aquí, todos los caracteres fueron reconocidos como tokens válidos
        # Pero según las reglas del lenguaje, deben estar separados por espacios
        if len(tokens_encontrados) > 1:
            return False, []  # Múltiples tokens pegados = inválido
        
        return True, tokens_encontrados

    def escanear_linea(self, linea_completa):
        resultados_tokens_linea = []
        puntero_actual = 0
        
        while puntero_actual < len(linea_completa):
            if linea_completa[puntero_actual].isspace():
                puntero_actual += 1
                continue

            # Verificar si toda la secuencia sin espacios es válida
            es_valida, tokens = self._es_secuencia_completa_valida(linea_completa, puntero_actual)
            
            if es_valida and len(tokens) == 1:
                # Es un solo token válido
                lexema = tokens[0]
                # Obtener la etiqueta del token
                _, etiqueta, nuevo_puntero = self._simular_nfa_epsilon_para_token(linea_completa, puntero_actual)
                if etiqueta:
                    resultados_tokens_linea.append(etiqueta)
                    puntero_actual = nuevo_puntero
                else:
                    # Fallback: consumir como inválido
                    _, nuevo_puntero = self._consumir_token_invalido(linea_completa, puntero_actual)
                    resultados_tokens_linea.append("INVALIDO")
                    puntero_actual = nuevo_puntero
            else:
                # La secuencia completa es inválida
                _, nuevo_puntero = self._consumir_token_invalido(linea_completa, puntero_actual)
                resultados_tokens_linea.append("INVALIDO")
                puntero_actual = nuevo_puntero

        return resultados_tokens_linea

    def analizar_archivo(self, ruta_archivo_fuente):
        resultados_completos = []
        with open(ruta_archivo_fuente, 'r', encoding='utf-8') as archivo:
            for linea_completa_raw in archivo:
                linea_completa = linea_completa_raw.strip()
                if not linea_completa:
                    continue
                tokens_encontrados = self.escanear_linea(linea_completa)
                resultados_completos.append([linea_completa, tokens_encontrados])
        return resultados_completos


if __name__ == "__main__":
    ruta_jff = "automataFinal.jff"
    ruta_cadenas = "validador.txt"

    analizador = AFD(ruta_jff)
    resultados_analisis = analizador.analizar_archivo(ruta_cadenas)

    for resultado_linea in resultados_analisis:
        linea_original = resultado_linea[0]
        tokens = resultado_linea[1]
        descripciones = "".join(f"({etiqueta})" for etiqueta in tokens)
        print(f"{linea_original:<30} → {descripciones}")