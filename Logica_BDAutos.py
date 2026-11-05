#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Funcionamiento de BDAutos: 25 consultas, MongoDB y administración de consultas.

Este módulo se importa desde Interfaz_BDAutos.py; no se ejecuta directamente.
"""

import copy
import json
import os
import queue
from pathlib import Path
from tkinter import messagebox, simpledialog

# Las consultas se basan en el modelo previamente migrado:
# autos, fabricantes y continentes; las especificaciones están embebidas.
# La aplicación enseña el mismo pipeline MongoDB que ejecuta con PyMongo.
CONSULTAS = json.loads(r'''[{"number":1,"title":"Autos 2024+ con al menos 35 mpg","collection":"autos","pipeline":[{"$match":{"especificaciones.year":{"$gte":2024},"especificaciones.mpg":{"$gte":35}}},{"$project":{"_id":0,"descripcion":1,"anio":"$especificaciones.year","mpg":"$especificaciones.mpg"}},{"$sort":{"mpg":-1,"descripcion":1}}],"descripcion":"Obtener los autos de modelo 2024 en adelante con rendimiento de al menos 35 mpg. Mostrar descripción, año y rendimiento, ordenados de mayor a menor rendimiento."},{"number":2,"title":"Fabricantes europeos: 4 cilindros y 250 hp o mas","collection":"autos","pipeline":[{"$lookup":{"from":"fabricantes","localField":"idMaker","foreignField":"_id","as":"fabricante"}},{"$unwind":"$fabricante"},{"$set":{"fabricante.origen":{"pais":{"$ifNull":["$fabricante.origen.pais","$fabricante.pais.nombre"]},"continente":{"$ifNull":["$fabricante.origen.continente","$fabricante.pais.continente"]}}}},{"$match":{"fabricante.origen.continente":"europe","especificaciones.cylinders":4,"especificaciones.horsepower":{"$gte":250}}},{"$project":{"_id":0,"descripcion":1,"pais":"$fabricante.origen.pais","potencia":"$especificaciones.horsepower"}},{"$sort":{"potencia":-1,"descripcion":1}}],"descripcion":"Listar los autos de fabricantes europeos con motor de 4 cilindros y al menos 250 hp. Mostrar descripción, país y potencia, ordenados por potencia descendente."},{"number":3,"title":"Cantidad de autos japoneses con motor turbo","collection":"autos","pipeline":[{"$lookup":{"from":"fabricantes","localField":"idMaker","foreignField":"_id","as":"fabricante"}},{"$unwind":"$fabricante"},{"$set":{"fabricante.origen":{"pais":{"$ifNull":["$fabricante.origen.pais","$fabricante.pais.nombre"]},"continente":{"$ifNull":["$fabricante.origen.continente","$fabricante.pais.continente"]}}}},{"$match":{"fabricante.origen.pais":"japan","descripcion":{"$regex":"\\d+(?:\\.\\d+)?t$","$options":"i"}}},{"$count":"totalAutosJaponesesTurbo"}],"descripcion":"Contar cuántos autos de fabricantes japoneses tienen motor turbo (su descripción termina con una cilindrada seguida de t, como 1.5t)."},{"number":4,"title":"Peso < 3000 y aceleracion < 9; O cilindros >= 8 y mpg >= 19","collection":"autos","pipeline":[{"$match":{"$or":[{"especificaciones.weight":{"$lt":3000},"especificaciones.accel":{"$lt":9}},{"especificaciones.cylinders":{"$gte":8},"especificaciones.mpg":{"$gte":19}}]}},{"$project":{"_id":0,"descripcion":1,"peso":"$especificaciones.weight","aceleracion":"$especificaciones.accel","cilindros":"$especificaciones.cylinders","mpg":"$especificaciones.mpg"}},{"$sort":{"descripcion":1}}],"descripcion":"Encontrar autos que pesen menos de 3000 lb y aceleren de 0 a 60 mph en menos de 9 s, o que tengan 8 o más cilindros y al menos 19 mpg."},{"number":5,"title":"Fabricantes con mas de una marca o modelo","collection":"fabricantes","pipeline":[{"$set":{"origen":{"pais":{"$ifNull":["$origen.pais","$pais.nombre"]},"continente":{"$ifNull":["$origen.continente","$pais.continente"]}}}},{"$match":{"modelos.1":{"$exists":true}}},{"$project":{"_id":0,"fabricante":"$maker","pais":"$origen.pais","modelos":"$modelos.nombre"}},{"$sort":{"fabricante":1}}],"descripcion":"Obtener los fabricantes que comercializan más de una marca o línea de modelo, mostrando su nombre, país y modelos."},{"number":6,"title":"Marca diferente del fabricante","collection":"autos","pipeline":[{"$lookup":{"from":"fabricantes","localField":"idMaker","foreignField":"_id","as":"fabricante"}},{"$unwind":"$fabricante"},{"$set":{"fabricante.origen":{"pais":{"$ifNull":["$fabricante.origen.pais","$fabricante.pais.nombre"]},"continente":{"$ifNull":["$fabricante.origen.continente","$fabricante.pais.continente"]}}}},{"$match":{"$expr":{"$ne":["$modelo.nombre","$fabricante.maker"]}}},{"$project":{"_id":0,"descripcion":1,"marca":"$modelo.nombre","fabricante":"$fabricante.maker"}},{"$sort":{"fabricante":1,"marca":1,"descripcion":1}}],"descripcion":"Encontrar los autos cuya marca es distinta del nombre de su grupo fabricante. Mostrar descripción, marca y fabricante."},{"number":7,"title":"Autos, mpg promedio y potencia promedio por pais","collection":"autos","pipeline":[{"$lookup":{"from":"fabricantes","localField":"idMaker","foreignField":"_id","as":"fabricante"}},{"$unwind":"$fabricante"},{"$set":{"fabricante.origen":{"pais":{"$ifNull":["$fabricante.origen.pais","$fabricante.pais.nombre"]},"continente":{"$ifNull":["$fabricante.origen.continente","$fabricante.pais.continente"]}}}},{"$group":{"_id":"$fabricante.origen.pais","numeroAutos":{"$sum":1},"promedioMpg":{"$avg":"$especificaciones.mpg"},"promedioHp":{"$avg":"$especificaciones.horsepower"}}},{"$project":{"_id":0,"pais":"$_id","numeroAutos":1,"promedioMpg":{"$round":["$promedioMpg",1]},"promedioHp":{"$round":["$promedioHp",1]}}},{"$sort":{"numeroAutos":-1,"pais":1}}],"descripcion":"Calcular por país el número de autos, el rendimiento promedio y la potencia promedio, redondeados a un decimal. Ordenar por número de autos."},{"number":8,"title":"Autos, marcas con autos y potencia promedio por fabricante","collection":"autos","pipeline":[{"$lookup":{"from":"fabricantes","localField":"idMaker","foreignField":"_id","as":"fabricante"}},{"$unwind":"$fabricante"},{"$set":{"fabricante.origen":{"pais":{"$ifNull":["$fabricante.origen.pais","$fabricante.pais.nombre"]},"continente":{"$ifNull":["$fabricante.origen.continente","$fabricante.pais.continente"]}}}},{"$group":{"_id":{"idMaker":"$idMaker","fabricante":"$fabricante.maker"},"numeroAutos":{"$sum":1},"marcasConAutos":{"$addToSet":"$modelo.modelID"},"promedioHp":{"$avg":"$especificaciones.horsepower"}}},{"$project":{"_id":0,"fabricante":"$_id.fabricante","numeroAutos":1,"numeroMarcas":{"$size":"$marcasConAutos"},"promedioHp":{"$round":["$promedioHp",1]}}},{"$sort":{"numeroAutos":-1,"fabricante":1}}],"descripcion":"Calcular por fabricante el número de autos, las marcas distintas con autos registrados y la potencia promedio (un decimal). Ordenar por número de autos."},{"number":9,"title":"Numero de marcas del catalogo por continente","collection":"continentes","pipeline":[{"$lookup":{"from":"fabricantes","let":{"nombreContinente":"$continente"},"pipeline":[{"$match":{"$expr":{"$eq":[{"$ifNull":["$origen.continente","$pais.continente"]},"$$nombreContinente"]}}}],"as":"fabricantes"}},{"$project":{"_id":0,"continente":1,"numeroModelos":{"$sum":{"$map":{"input":"$fabricantes","as":"f","in":{"$size":{"$ifNull":["$$f.modelos",[]]}}}}}}},{"$sort":{"numeroModelos":-1,"continente":1}}],"descripcion":"Contar cuántas marcas o modelos del catálogo hay por continente."},{"number":10,"title":"Rangos de rendimiento y peso promedio","collection":"autos","pipeline":[{"$set":{"rango":{"$switch":{"branches":[{"case":{"$lt":["$especificaciones.mpg",20]},"then":{"orden":1,"etiqueta":"[0,20)"}},{"case":{"$lt":["$especificaciones.mpg",25]},"then":{"orden":2,"etiqueta":"[20,25)"}},{"case":{"$lt":["$especificaciones.mpg",30]},"then":{"orden":3,"etiqueta":"[25,30)"}},{"case":{"$lt":["$especificaciones.mpg",35]},"then":{"orden":4,"etiqueta":"[30,35)"}},{"case":{"$lt":["$especificaciones.mpg",40]},"then":{"orden":5,"etiqueta":"[35,40)"}}],"default":{"orden":6,"etiqueta":"40 o mas"}}}}},{"$group":{"_id":"$rango.orden","rango":{"$first":"$rango.etiqueta"},"numeroAutos":{"$sum":1},"pesoPromedio":{"$avg":"$especificaciones.weight"}}},{"$project":{"_id":0,"orden":"$_id","rango":1,"numeroAutos":1,"pesoPromedio":{"$round":["$pesoPromedio",1]}}},{"$sort":{"orden":1}},{"$project":{"orden":0}}],"descripcion":"Clasificar los autos en rangos de mpg [0,20), [20,25), [25,30), [30,35), [35,40) y 40 o más; obtener el total y peso promedio por rango."},{"number":11,"title":"Top 5 fabricantes por mpg promedio (al menos 8 autos)","collection":"autos","pipeline":[{"$lookup":{"from":"fabricantes","localField":"idMaker","foreignField":"_id","as":"fabricante"}},{"$unwind":"$fabricante"},{"$set":{"fabricante.origen":{"pais":{"$ifNull":["$fabricante.origen.pais","$fabricante.pais.nombre"]},"continente":{"$ifNull":["$fabricante.origen.continente","$fabricante.pais.continente"]}}}},{"$group":{"_id":{"idMaker":"$idMaker","fabricante":"$fabricante.maker"},"numeroAutos":{"$sum":1},"promedioMpg":{"$avg":"$especificaciones.mpg"}}},{"$match":{"numeroAutos":{"$gte":8}}},{"$project":{"_id":0,"fabricante":"$_id.fabricante","numeroAutos":1,"promedioMpg":{"$round":["$promedioMpg",2]}}},{"$sort":{"promedioMpg":-1,"fabricante":1}},{"$limit":5}],"descripcion":"Obtener los 5 fabricantes con mayor rendimiento promedio, considerando únicamente fabricantes con al menos 8 autos registrados."},{"number":12,"title":"Categorias de mpg por continente","collection":"autos","pipeline":[{"$lookup":{"from":"fabricantes","localField":"idMaker","foreignField":"_id","as":"fabricante"}},{"$unwind":"$fabricante"},{"$set":{"fabricante.origen":{"pais":{"$ifNull":["$fabricante.origen.pais","$fabricante.pais.nombre"]},"continente":{"$ifNull":["$fabricante.origen.continente","$fabricante.pais.continente"]}}}},{"$set":{"categoria":{"$switch":{"branches":[{"case":{"$gte":["$especificaciones.mpg",30]},"then":"Alta"},{"case":{"$gte":["$especificaciones.mpg",20]},"then":"Media"}],"default":"Baja"}}}},{"$group":{"_id":{"continente":"$fabricante.origen.continente","categoria":"$categoria"},"numeroAutos":{"$sum":1}}},{"$project":{"_id":0,"continente":"$_id.continente","categoria":"$_id.categoria","numeroAutos":1}},{"$sort":{"continente":1,"categoria":1}}],"descripcion":"Clasificar los autos por rendimiento: Alta (≥30 mpg), Media (20 a menos de 30 mpg) y Baja (<20 mpg), y contar por continente y categoría."},{"number":13,"title":"Total de autos por fabricante, incluyendo cero","collection":"fabricantes","pipeline":[{"$lookup":{"from":"autos","localField":"_id","foreignField":"idMaker","as":"autosRegistrados"}},{"$project":{"_id":0,"fabricante":"$maker","nombreCompleto":"$fullName","numeroAutos":{"$size":"$autosRegistrados"}}},{"$sort":{"numeroAutos":-1,"fabricante":1}}],"descripcion":"Desde la colección de fabricantes, contar cuántos autos tiene registrado cada fabricante, incluyendo los fabricantes con cero autos."},{"number":14,"title":"Modelos del catalogo sin autos registrados","collection":"fabricantes","pipeline":[{"$unwind":"$modelos"},{"$lookup":{"from":"autos","localField":"modelos.modelID","foreignField":"modelo.modelID","as":"autosDelModelo"}},{"$match":{"autosDelModelo":{"$size":0}}},{"$project":{"_id":0,"modelID":"$modelos.modelID","marca":"$modelos.nombre","fabricante":"$maker"}},{"$sort":{"fabricante":1,"marca":1}}],"descripcion":"Encontrar las marcas o modelos del catálogo que no tienen ningún auto registrado."},{"number":15,"title":"Cinco autos mas potentes","collection":"autos","pipeline":[{"$lookup":{"from":"fabricantes","localField":"idMaker","foreignField":"_id","as":"fabricante"}},{"$unwind":"$fabricante"},{"$set":{"fabricante.origen":{"pais":{"$ifNull":["$fabricante.origen.pais","$fabricante.pais.nombre"]},"continente":{"$ifNull":["$fabricante.origen.continente","$fabricante.pais.continente"]}}}},{"$sort":{"especificaciones.horsepower":-1,"_id":1}},{"$limit":5},{"$project":{"_id":0,"descripcion":1,"potenciaHp":"$especificaciones.horsepower","fabricante":"$fabricante.fullName"}}],"descripcion":"Obtener los 5 autos más potentes con descripción, potencia y nombre completo de su fabricante."},{"number":16,"title":"Top 3 autos por mpg en cada continente","collection":"autos","pipeline":[{"$lookup":{"from":"fabricantes","localField":"idMaker","foreignField":"_id","as":"fabricante"}},{"$unwind":"$fabricante"},{"$set":{"fabricante.origen":{"pais":{"$ifNull":["$fabricante.origen.pais","$fabricante.pais.nombre"]},"continente":{"$ifNull":["$fabricante.origen.continente","$fabricante.pais.continente"]}}}},{"$setWindowFields":{"partitionBy":"$fabricante.origen.continente","sortBy":{"especificaciones.mpg":-1},"output":{"posicion":{"$documentNumber":{}}}}},{"$match":{"posicion":{"$lte":3}}},{"$project":{"_id":0,"continente":"$fabricante.origen.continente","posicion":1,"descripcion":1,"mpg":"$especificaciones.mpg"}},{"$sort":{"continente":1,"posicion":1}}],"descripcion":"Obtener los 3 autos con mejor rendimiento en mpg por cada continente; mostrar descripción y rendimiento."},{"number":17,"title":"Marca con mas autos de cada fabricante multimarca","collection":"fabricantes","pipeline":[{"$match":{"modelos.1":{"$exists":true}}},{"$unwind":"$modelos"},{"$lookup":{"from":"autos","localField":"modelos.modelID","foreignField":"modelo.modelID","as":"autosDeMarca"}},{"$set":{"numeroAutosMarca":{"$size":"$autosDeMarca"}}},{"$sort":{"_id":1,"numeroAutosMarca":-1,"modelos.nombre":1}},{"$group":{"_id":"$_id","fabricante":{"$first":"$maker"},"marca":{"$first":"$modelos.nombre"},"numeroAutos":{"$first":"$numeroAutosMarca"}}},{"$project":{"_id":0,"fabricante":1,"marca":1,"numeroAutos":1}},{"$sort":{"fabricante":1}}],"descripcion":"Para cada fabricante que tiene más de un modelo, determinar cuál de sus modelos posee la mayor cantidad de autos registrados."},{"number":18,"title":"Porcentaje del total de autos por continente","collection":"continentes","pipeline":[{"$lookup":{"from":"fabricantes","let":{"nombreContinente":"$continente"},"pipeline":[{"$match":{"$expr":{"$eq":[{"$ifNull":["$origen.continente","$pais.continente"]},"$$nombreContinente"]}}}],"as":"fabricantes"}},{"$lookup":{"from":"autos","localField":"fabricantes._id","foreignField":"idMaker","as":"autosDelContinente"}},{"$lookup":{"from":"autos","pipeline":[{"$count":"total"}],"as":"totalGeneral"}},{"$set":{"numeroAutos":{"$size":"$autosDelContinente"},"totalAutos":{"$ifNull":[{"$arrayElemAt":["$totalGeneral.total",0]},0]}}},{"$project":{"_id":0,"continente":1,"numeroAutos":1,"porcentaje":{"$cond":[{"$eq":["$totalAutos",0]},0,{"$round":[{"$multiply":[{"$divide":["$numeroAutos","$totalAutos"]},100]},2]}]}}},{"$sort":{"numeroAutos":-1,"continente":1}}],"descripcion":"Calcular qué porcentaje del total de autos representa cada continente, con dos decimales."},{"number":19,"title":"Cinco autos sobre el promedio de mpg de sus cilindros","collection":"autos","pipeline":[{"$setWindowFields":{"partitionBy":"$especificaciones.cylinders","output":{"promedioGrupo":{"$avg":"$especificaciones.mpg","window":{"documents":["unbounded","unbounded"]}}}}},{"$set":{"diferencia":{"$subtract":["$especificaciones.mpg","$promedioGrupo"]}}},{"$sort":{"diferencia":-1,"_id":1}},{"$limit":5},{"$project":{"_id":0,"descripcion":1,"cilindros":"$especificaciones.cylinders","mpg":"$especificaciones.mpg","promedioMismosCilindros":{"$round":["$promedioGrupo",2]},"diferenciaMpg":{"$round":["$diferencia",2]}}}],"descripcion":"Listar los 5 autos cuyo rendimiento supera más el promedio de los autos con el mismo número de cilindros. Mostrar promedio y diferencia."},{"number":20,"title":"Autos con 8 o mas cilindros por continente","collection":"continentes","pipeline":[{"$lookup":{"from":"fabricantes","let":{"nombreContinente":"$continente"},"pipeline":[{"$match":{"$expr":{"$eq":[{"$ifNull":["$origen.continente","$pais.continente"]},"$$nombreContinente"]}}}],"as":"fabricantes"}},{"$lookup":{"from":"autos","localField":"fabricantes._id","foreignField":"idMaker","as":"autosDelContinente"}},{"$set":{"numeroAutos":{"$size":"$autosDelContinente"},"autos8OMasCilindros":{"$size":{"$filter":{"input":"$autosDelContinente","as":"a","cond":{"$gte":["$$a.especificaciones.cylinders",8]}}}}}},{"$project":{"_id":0,"continente":1,"numeroAutos":1,"autos8OMasCilindros":1,"porcentaje":{"$cond":[{"$eq":["$numeroAutos",0]},0,{"$round":[{"$multiply":[{"$divide":["$autos8OMasCilindros","$numeroAutos"]},100]},1]}]}}},{"$sort":{"continente":1}}],"descripcion":"Por continente, calcular total de autos, cuántos tienen 8 o más cilindros y qué porcentaje representan (un decimal)."},{"number":21,"title":"Top 10 hp por 1000 lb","collection":"autos","pipeline":[{"$lookup":{"from":"fabricantes","localField":"idMaker","foreignField":"_id","as":"fabricante"}},{"$unwind":"$fabricante"},{"$set":{"fabricante.origen":{"pais":{"$ifNull":["$fabricante.origen.pais","$fabricante.pais.nombre"]},"continente":{"$ifNull":["$fabricante.origen.continente","$fabricante.pais.continente"]}}}},{"$match":{"especificaciones.weight":{"$gt":0}}},{"$set":{"potenciaPor1000Lb":{"$multiply":[{"$divide":["$especificaciones.horsepower","$especificaciones.weight"]},1000]}}},{"$sort":{"potenciaPor1000Lb":-1,"_id":1}},{"$limit":10},{"$project":{"_id":0,"descripcion":1,"pais":"$fabricante.origen.pais","potenciaHp":"$especificaciones.horsepower","pesoLb":"$especificaciones.weight","potenciaPor1000Lb":{"$round":["$potenciaPor1000Lb",2]}}}],"descripcion":"Calcular potencia por cada 1000 lb de peso y mostrar los 10 autos con el valor más alto, incluyendo su país."},{"number":22,"title":"Modelos que no se llaman igual que su fabricante","collection":"fabricantes","pipeline":[{"$set":{"modelosDistintos":{"$filter":{"input":"$modelos","as":"m","cond":{"$ne":["$$m.nombre","$maker"]}}}}},{"$match":{"modelosDistintos.0":{"$exists":true}}},{"$project":{"_id":0,"fabricante":"$maker","modelos":"$modelosDistintos.nombre"}},{"$sort":{"fabricante":1}}],"descripcion":"Para cada fabricante, mostrar únicamente modelos cuyo nombre sea distinto al del fabricante. Excluir fabricantes sin modelos diferentes."},{"number":23,"title":"Facet: autos por continente, por cilindros y estadisticas de mpg","collection":"autos","pipeline":[{"$facet":{"porContinente":[{"$lookup":{"from":"fabricantes","localField":"idMaker","foreignField":"_id","as":"fabricante"}},{"$unwind":"$fabricante"},{"$set":{"fabricante.origen":{"pais":{"$ifNull":["$fabricante.origen.pais","$fabricante.pais.nombre"]},"continente":{"$ifNull":["$fabricante.origen.continente","$fabricante.pais.continente"]}}}},{"$group":{"_id":"$fabricante.origen.continente","numeroAutos":{"$sum":1}}},{"$project":{"_id":0,"continente":"$_id","numeroAutos":1}},{"$sort":{"numeroAutos":-1,"continente":1}}],"porCilindros":[{"$group":{"_id":"$especificaciones.cylinders","numeroAutos":{"$sum":1}}},{"$project":{"_id":0,"cilindros":"$_id","numeroAutos":1}},{"$sort":{"cilindros":1}}],"estadisticasGlobalesMpg":[{"$group":{"_id":null,"minimo":{"$min":"$especificaciones.mpg"},"maximo":{"$max":"$especificaciones.mpg"},"promedio":{"$avg":"$especificaciones.mpg"}}},{"$project":{"_id":0,"minimo":1,"maximo":1,"promedio":{"$round":["$promedio",2]}}}]}}],"descripcion":"En una sola consulta: número de autos por continente, número de autos por cilindros y estadísticas globales de mpg (mínimo, máximo y promedio)."},{"number":24,"title":"Cinco autos alemanes mejor posicionados por potencia","collection":"autos","pipeline":[{"$lookup":{"from":"fabricantes","localField":"idMaker","foreignField":"_id","as":"fabricante"}},{"$unwind":"$fabricante"},{"$set":{"fabricante.origen":{"pais":{"$ifNull":["$fabricante.origen.pais","$fabricante.pais.nombre"]},"continente":{"$ifNull":["$fabricante.origen.continente","$fabricante.pais.continente"]}}}},{"$match":{"fabricante.origen.pais":"germany"}},{"$setWindowFields":{"partitionBy":"$fabricante.origen.pais","sortBy":{"especificaciones.horsepower":-1},"output":{"posicion":{"$documentNumber":{}}}}},{"$match":{"posicion":{"$lte":5}}},{"$project":{"_id":0,"posicion":1,"descripcion":1,"pais":"$fabricante.origen.pais","potenciaHp":"$especificaciones.horsepower"}},{"$sort":{"posicion":1}}],"descripcion":"Asignar a cada auto alemán su posición por potencia dentro de su país y mostrar los 5 primeros."},{"number":25,"title":"Auto con mejor mpg de cada fabricante europeo","collection":"fabricantes","pipeline":[{"$set":{"origen":{"pais":{"$ifNull":["$origen.pais","$pais.nombre"]},"continente":{"$ifNull":["$origen.continente","$pais.continente"]}}}},{"$match":{"origen.continente":"europe"}},{"$lookup":{"from":"autos","localField":"_id","foreignField":"idMaker","pipeline":[{"$sort":{"especificaciones.mpg":-1,"_id":1}},{"$limit":1},{"$project":{"_id":0,"descripcion":1,"mpg":"$especificaciones.mpg"}}],"as":"autoMasEficiente"}},{"$unwind":{"path":"$autoMasEficiente","preserveNullAndEmptyArrays":true}},{"$project":{"_id":0,"fabricante":"$maker","pais":"$origen.pais","auto":{"$ifNull":["$autoMasEficiente.descripcion","Sin autos registrados"]},"mpg":{"$ifNull":["$autoMasEficiente.mpg",null]}}},{"$sort":{"fabricante":1}}],"descripcion":"Obtener para cada fabricante europeo su auto más eficiente por rendimiento en mpg."}]''')

RUTA_DATOS = Path(os.environ.get(
    "BDAUTOS_CONSULTAS_FILE",
    str(Path(__file__).with_name("consultas_guardadas.json"))
))

def codigo_mongodb(consulta):
    """Genera el código de mongosh correspondiente a lo que ejecuta PyMongo."""
    coleccion = consulta["collection"]
    tipo = consulta.get("tipo", "aggregate")
    if tipo == "aggregate":
        return "db." + coleccion + ".aggregate(" + json.dumps(
            consulta["pipeline"], ensure_ascii=False, indent=2
        ) + ")"
    filtro = json.dumps(consulta["filtro"], ensure_ascii=False, indent=2)
    if tipo == "countDocuments":
        return "db." + coleccion + ".countDocuments(" + filtro + ")"
    if tipo == "find":
        return "db." + coleccion + ".find(" + filtro + ")"
    raise ValueError("Operación no admitida: " + tipo)

def formato_resultados(documentos):
    if not documentos:
        return "Sin resultados.\n\nLa consulta se ejecutó correctamente."
    return f"Resultados obtenidos: {len(documentos)}\n\n" + json.dumps(
        documentos, ensure_ascii=False, indent=2, default=str
    )

def _sin_escritura(valor):
    """Impide etapas que pueden modificar la base de datos en consultas nuevas."""
    if isinstance(valor, dict):
        for llave, contenido in valor.items():
            if llave in ("$out", "$merge", "$where", "$function", "$accumulator"):
                return False
            if not _sin_escritura(contenido):
                return False
    elif isinstance(valor, list):
        return all(_sin_escritura(x) for x in valor)
    return True

class LogicaCrearConsulta(object):
    """Validación, almacenamiento y ejecución de consultas nuevas."""

    def cambiar_ejemplo(self, _=None):
        tipo = self.tipo.get()
        if tipo == "aggregate":
            ejemplo = "[\n  {\"$match\": {\"especificaciones.year\": 2024}},\n  {\"$limit\": 10}\n]"
        else:
            ejemplo = "{\n  \"especificaciones.year\": 2024\n}"
        self.json_editor.delete("1.0", "end")
        self.json_editor.insert("1.0", ejemplo)

    def guardar(self):
        nombre = self.nombre.get().strip()
        descripcion = self.descripcion.get().strip()
        if not nombre or not descripcion:
            self._mensaje_estado("Completa el nombre y la descripción.", error=True)
            messagebox.showwarning("Faltan datos", "Escribe un nombre y una descripción.", parent=self)
            return
        try:
            consulta_json = json.loads(self.json_editor.get("1.0", "end-1c"))
        except json.JSONDecodeError as e:
            self._mensaje_estado("Error en el formato JSON.", error=True)
            messagebox.showerror(
                "JSON incorrecto",
                f"Revisa el JSON en la línea {e.lineno}, columna {e.colno}: {e.msg}.\n\n"
                "Escribe los nombres de campos entre comillas dobles.", parent=self
            )
            return
        tipo = self.tipo.get()
        if tipo == "aggregate" and not (
            isinstance(consulta_json, list) and
            all(isinstance(etapa, dict) and len(etapa) == 1 for etapa in consulta_json)
        ):
            self._mensaje_estado("La consulta aggregate no es válida.", error=True)
            messagebox.showerror(
                "Consulta inválida", "aggregate requiere una lista de etapas JSON; "
                "cada etapa contiene un solo operador, como $match, $group o $sort.", parent=self
            )
            return
        if tipo != "aggregate" and not isinstance(consulta_json, dict):
            self._mensaje_estado("El filtro debe ser un objeto JSON.", error=True)
            messagebox.showerror("Consulta inválida", "find y countDocuments requieren un objeto JSON.", parent=self)
            return
        if not _sin_escritura(consulta_json):
            self._mensaje_estado("Solo se permiten consultas de lectura.", error=True)
            messagebox.showerror("Operación no permitida", "La aplicación admite solo consultas de lectura.", parent=self)
            return
        resultado = {
            "number": self.app.proximo_numero(),
            "title": nombre,
            "descripcion": descripcion,
            "collection": self.coleccion.get(),
            "tipo": tipo,
        }
        if tipo == "aggregate":
            resultado["pipeline"] = consulta_json
        else:
            resultado["filtro"] = consulta_json
        if self.app.agregar_consulta(resultado):
            self._mensaje_estado("Consulta guardada correctamente.")
            self.resultado = resultado
            self.after(180, self.destroy)


class LogicaAutos(object):
    """Gestión de consultas y conexión; recibe controles gráficos de la interfaz."""

    def _cargar_estado(self):
        if not RUTA_DATOS.exists():
            return {"eliminadas": [], "nuevas": []}
        try:
            contenido = json.loads(RUTA_DATOS.read_text(encoding="utf-8"))
            if not isinstance(contenido.get("eliminadas"), list) or not isinstance(contenido.get("nuevas"), list):
                raise ValueError("Formato de archivo inesperado")
            return contenido
        except (OSError, ValueError) as e:
            messagebox.showwarning(
                "Consultas guardadas", "No se pudieron leer las consultas personales. "
                f"Se cargarán las 25 originales.\n\n{e}", parent=self.raiz
            )
            return {"eliminadas": [], "nuevas": []}

    def _consultas_visibles(self):
        ocultas = set(self.estado_guardado["eliminadas"])
        originales = [copy.deepcopy(q) for q in CONSULTAS if q["number"] not in ocultas]
        nuevas = [copy.deepcopy(q) for q in self.estado_guardado["nuevas"]]
        return sorted(originales + nuevas, key=lambda q: q["number"])

    def _guardar_estado(self, nuevo_estado):
        try:
            RUTA_DATOS.parent.mkdir(parents=True, exist_ok=True)
            temporal = RUTA_DATOS.with_suffix(".tmp")
            temporal.write_text(json.dumps(nuevo_estado, indent=2, ensure_ascii=False), encoding="utf-8")
            temporal.replace(RUTA_DATOS)
        except OSError as e:
            messagebox.showerror(
                "No se pudo guardar", "Revisa los permisos de la carpeta del programa.\n\n" + str(e),
                parent=self.raiz
            )
            return False
        self.estado_guardado = nuevo_estado
        self.consultas = self._consultas_visibles()
        return True

    def proximo_numero(self):
        todos = [q["number"] for q in CONSULTAS + self.estado_guardado["nuevas"]]
        return max(todos, default=0) + 1

    def agregar_consulta(self, consulta):
        nuevo = copy.deepcopy(self.estado_guardado)
        nuevo["nuevas"].append(consulta)
        if not self._guardar_estado(nuevo):
            return False
        self._actualizar_botones()
        self.seleccionar_consulta(consulta["number"])
        self.raiz.after(80, lambda: self.canvas_lateral.yview_moveto(1.0))
        return True

    def eliminar_consulta(self):
        numero = self.seleccion_actual
        consulta = next((q for q in self.consultas if q["number"] == numero), None)
        if consulta is None:
            messagebox.showinfo("Eliminar consulta", "Primero selecciona una consulta.", parent=self.raiz)
            return
        if not messagebox.askyesno(
            "Eliminar consulta", f"¿Eliminar la Consulta {numero}: {consulta['title']}?\n\n"
            "La decisión se guardará. Puedes recuperar las consultas originales con «Restaurar 25».",
            parent=self.raiz
        ):
            return
        nuevo = copy.deepcopy(self.estado_guardado)
        if numero <= 25:
            if numero not in nuevo["eliminadas"]:
                nuevo["eliminadas"].append(numero)
        else:
            nuevo["nuevas"] = [q for q in nuevo["nuevas"] if q["number"] != numero]
        if not self._guardar_estado(nuevo):
            return
        self.folio += 1
        self.seleccion_actual = None
        self._actualizar_botones()
        if self.consultas:
            siguiente = next((q["number"] for q in self.consultas if q["number"] > numero), self.consultas[-1]["number"])
            self.seleccionar_consulta(siguiente)
        else:
            self.texto_descripcion.configure(text="No hay consultas. Crea una nueva o restaura las originales.")
            self._escribir(self.codigo, "")
            self._escribir(self.resultado, "")

    def restaurar_originales(self):
        borradas = self.estado_guardado["eliminadas"]
        if not borradas:
            messagebox.showinfo("Restaurar", "Las 25 consultas originales están disponibles.", parent=self.raiz)
            return
        if not messagebox.askyesno(
            "Restaurar originales", "¿Restaurar las consultas originales eliminadas?\n\n"
            "Tus consultas personalizadas se conservarán.", parent=self.raiz
        ):
            return
        nuevo = copy.deepcopy(self.estado_guardado)
        nuevo["eliminadas"] = []
        if self._guardar_estado(nuevo):
            self._actualizar_botones()
            self.seleccionar_consulta(1)

    def _consultar(self, consulta, folio, uri, base_preferida):
        cliente = None
        try:
            try:
                from pymongo import MongoClient
            except ImportError as err:
                raise RuntimeError(
                    "Falta PyMongo. Instálalo con: python -m pip install pymongo"
                ) from err
            cliente = MongoClient(uri, serverSelectionTimeoutMS=4500, connectTimeoutMS=4500)
            cliente.admin.command("ping")
            nombres = list(dict.fromkeys([base_preferida, "BDAutos", "Autos"]))
            elegida = None
            for nombre in nombres:
                base = cliente[nombre]
                if base["autos"].count_documents({}, limit=1) > 0:
                    elegida = base
                    break
            if elegida is None:
                raise RuntimeError(
                    "No se encontraron autos en las bases " + ", ".join(nombres) + ".\n\n"
                    "Primero ejecuta la migración y revisa en mongosh:\n"
                    "db.getSiblingDB('BDAutos').autos.findOne()"
                )
            coleccion = elegida[consulta["collection"]]
            tipo = consulta.get("tipo", "aggregate")
            if tipo == "aggregate":
                documentos = list(coleccion.aggregate(copy.deepcopy(consulta["pipeline"]), allowDiskUse=True))
            elif tipo == "find":
                documentos = list(coleccion.find(copy.deepcopy(consulta["filtro"])).limit(1000))
            elif tipo == "countDocuments":
                documentos = [{"total": coleccion.count_documents(copy.deepcopy(consulta["filtro"]))}]
            else:
                raise ValueError("Operación no admitida: " + tipo)
            if consulta["number"] == 3 and not documentos:
                documentos = [{"totalAutosJaponesesTurbo": 0}]
            self.mensajes.put((folio, True, formato_resultados(documentos), elegida.name, len(documentos)))
        except Exception as e:
            mensaje = str(e)
            if "Unrecognized pipeline stage" in mensaje or "not allowed in this context" in mensaje:
                mensaje += "\n\nAlgunas consultas necesitan MongoDB 5.0 o posterior."
            self.mensajes.put((folio, False, mensaje, None, 0))
        finally:
            if cliente is not None:
                cliente.close()

    def _revisar_mensajes(self):
        try:
            while True:
                folio, correcto, texto, base, cuantos = self.mensajes.get_nowait()
                if folio != self.folio:
                    continue
                if correcto:
                    self.base_actual = base
                    self._escribir(self.resultado, texto)
                else:
                    self._escribir(self.resultado, "NO SE PUDO EJECUTAR LA CONSULTA\n\n" + texto)
        except queue.Empty:
            pass
        self.raiz.after(130, self._revisar_mensajes)

    def configurar_conexion(self):
        nueva_uri = simpledialog.askstring(
            "Conexión MongoDB", "URI de MongoDB (por ejemplo mongodb://localhost:27017):",
            initialvalue=self.uri, parent=self.raiz
        )
        if nueva_uri is None:
            return
        if not nueva_uri.strip():
            messagebox.showwarning("Conexión", "La URI no puede estar vacía.", parent=self.raiz)
            return
        nueva_base = simpledialog.askstring(
            "Base de datos", "Nombre de base de datos:",
            initialvalue=self.base_preferida, parent=self.raiz
        )
        if nueva_base is None:
            return
        self.uri = nueva_uri.strip()
        self.base_preferida = nueva_base.strip() or "BDAutos"
        if self.seleccion_actual is not None:
            self.seleccionar_consulta(self.seleccion_actual)

    def _copiar(self, editor):
        self.raiz.clipboard_clear()
        self.raiz.clipboard_append(editor.get("1.0", "end-1c"))

    def copiar_codigo(self):
        self._copiar(self.codigo)

    def copiar_resultado(self):
        self._copiar(self.resultado)
