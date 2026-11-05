//CONSULTAS DE LA BASE DE DATOS DE AUTOS

// 1. Autos 2024 en adelante con al menos 35 mpg; ordenar de mayor a menor mpg.
mostrar(1, "Autos 2024+ con al menos 35 mpg", autos.aggregate([
  { $match: { "especificaciones.year": { $gte: 2024 }, "especificaciones.mpg": { $gte: 35 } } },
  { $project: { _id: 0, descripcion: 1, anio: "$especificaciones.year", mpg: "$especificaciones.mpg" } },
  { $sort: { mpg: -1, descripcion: 1 } }
]));

// 2. Autos de fabricantes europeos: 4 cilindros y 250 hp o mas.
mostrar(2, "Fabricantes europeos: 4 cilindros y 250 hp o mas", autos.aggregate([
  ...unirFabricante,
  { $match: { "fabricante.origen.continente": "europe", "especificaciones.cylinders": 4, "especificaciones.horsepower": { $gte: 250 } } },
  { $project: { _id: 0, descripcion: 1, pais: "$fabricante.origen.pais", potencia: "$especificaciones.horsepower" } },
  { $sort: { potencia: -1, descripcion: 1 } }
]));

// 3. Cuantos autos de fabricantes japoneses tienen cilindrada terminada en "t" (turbo).
mostrar(3, "Cantidad de autos japoneses con motor turbo", autos.aggregate([
  ...unirFabricante,
  { $match: { "fabricante.origen.pais": "japan", descripcion: /\d+(?:\.\d+)?t$/i } },
  { $count: "totalAutosJaponesesTurbo" }
]));

// 4. Autos que cumplen cualquiera de las dos condiciones del enunciado.
mostrar(4, "Peso < 3000 y aceleracion < 9; O cilindros >= 8 y mpg >= 19", autos.aggregate([
  { $match: { $or: [
    { "especificaciones.weight": { $lt: 3000 }, "especificaciones.accel": { $lt: 9 } },
    { "especificaciones.cylinders": { $gte: 8 }, "especificaciones.mpg": { $gte: 19 } }
  ] } },
  { $project: { _id: 0, descripcion: 1, peso: "$especificaciones.weight", aceleracion: "$especificaciones.accel", cilindros: "$especificaciones.cylinders", mpg: "$especificaciones.mpg" } },
  { $sort: { descripcion: 1 } }
]));

// 5. Fabricantes con mas de un modelo (marca) en su catalogo.
mostrar(5, "Fabricantes con mas de una marca o modelo", fabricantes.aggregate([
  ...normalizarFabricante,
  { $match: { "modelos.1": { $exists: true } } },
  { $project: { _id: 0, fabricante: "$maker", pais: "$origen.pais", modelos: "$modelos.nombre" } },
  { $sort: { fabricante: 1 } }
]));

// 6. Autos cuya marca es distinta al nombre corto de su grupo fabricante.
mostrar(6, "Marca diferente del fabricante", autos.aggregate([
  ...unirFabricante,
  { $match: { $expr: { $ne: ["$modelo.nombre", "$fabricante.maker"] } } },
  { $project: { _id: 0, descripcion: 1, marca: "$modelo.nombre", fabricante: "$fabricante.maker" } },
  { $sort: { fabricante: 1, marca: 1, descripcion: 1 } }
]));

// 7. Numero de autos y promedios de mpg y potencia por pais.
mostrar(7, "Autos, mpg promedio y potencia promedio por pais", autos.aggregate([
  ...unirFabricante,
  { $group: { _id: "$fabricante.origen.pais", numeroAutos: { $sum: 1 }, promedioMpg: { $avg: "$especificaciones.mpg" }, promedioHp: { $avg: "$especificaciones.horsepower" } } },
  { $project: { _id: 0, pais: "$_id", numeroAutos: 1, promedioMpg: { $round: ["$promedioMpg", 1] }, promedioHp: { $round: ["$promedioHp", 1] } } },
  { $sort: { numeroAutos: -1, pais: 1 } }
]));

// 8. Autos por fabricante, numero de marcas CON autos y potencia promedio.
mostrar(8, "Autos, marcas con autos y potencia promedio por fabricante", autos.aggregate([
  ...unirFabricante,
  { $group: { _id: { idMaker: "$idMaker", fabricante: "$fabricante.maker" }, numeroAutos: { $sum: 1 }, marcasConAutos: { $addToSet: "$modelo.modelID" }, promedioHp: { $avg: "$especificaciones.horsepower" } } },
  { $project: { _id: 0, fabricante: "$_id.fabricante", numeroAutos: 1, numeroMarcas: { $size: "$marcasConAutos" }, promedioHp: { $round: ["$promedioHp", 1] } } },
  { $sort: { numeroAutos: -1, fabricante: 1 } }
]));

// 9. Cuantas marcas del catalogo hay por continente (incluye 0).
mostrar(9, "Numero de marcas del catalogo por continente", continentes.aggregate([
  ...unirFabricantesPorContinente,
  { $project: { _id: 0, continente: 1, numeroModelos: { $sum: { $map: { input: "$fabricantes", as: "f", in: { $size: { $ifNull: ["$$f.modelos", []] } } } } } } },
  { $sort: { numeroModelos: -1, continente: 1 } }
]));

// 10. Agrupar autos por rangos de mpg; contar y calcular peso promedio.
mostrar(10, "Rangos de rendimiento y peso promedio", autos.aggregate([
  { $set: { rango: { $switch: { branches: [
    { case: { $lt: ["$especificaciones.mpg", 20] }, then: { orden: 1, etiqueta: "[0,20)" } },
    { case: { $lt: ["$especificaciones.mpg", 25] }, then: { orden: 2, etiqueta: "[20,25)" } },
    { case: { $lt: ["$especificaciones.mpg", 30] }, then: { orden: 3, etiqueta: "[25,30)" } },
    { case: { $lt: ["$especificaciones.mpg", 35] }, then: { orden: 4, etiqueta: "[30,35)" } },
    { case: { $lt: ["$especificaciones.mpg", 40] }, then: { orden: 5, etiqueta: "[35,40)" } }
  ], default: { orden: 6, etiqueta: "40 o mas" } } } } },
  { $group: { _id: "$rango.orden", rango: { $first: "$rango.etiqueta" }, numeroAutos: { $sum: 1 }, pesoPromedio: { $avg: "$especificaciones.weight" } } },
  { $project: { _id: 0, orden: "$_id", rango: 1, numeroAutos: 1, pesoPromedio: { $round: ["$pesoPromedio", 1] } } },
  { $sort: { orden: 1 } },
  { $project: { orden: 0 } }
]));

// 11. Cinco fabricantes con mayor promedio mpg, con minimo 8 autos.
mostrar(11, "Top 5 fabricantes por mpg promedio (al menos 8 autos)", autos.aggregate([
  ...unirFabricante,
  { $group: { _id: { idMaker: "$idMaker", fabricante: "$fabricante.maker" }, numeroAutos: { $sum: 1 }, promedioMpg: { $avg: "$especificaciones.mpg" } } },
  { $match: { numeroAutos: { $gte: 8 } } },
  { $project: { _id: 0, fabricante: "$_id.fabricante", numeroAutos: 1, promedioMpg: { $round: ["$promedioMpg", 2] } } },
  { $sort: { promedioMpg: -1, fabricante: 1 } },
  { $limit: 5 }
]));

// 12. Clasificar cada auto Alta, Media o Baja; contar por continente y categoria.
mostrar(12, "Categorias de mpg por continente", autos.aggregate([
  ...unirFabricante,
  { $set: { categoria: { $switch: { branches: [
    { case: { $gte: ["$especificaciones.mpg", 30] }, then: "Alta" },
    { case: { $gte: ["$especificaciones.mpg", 20] }, then: "Media" }
  ], default: "Baja" } } } },
  { $group: { _id: { continente: "$fabricante.origen.continente", categoria: "$categoria" }, numeroAutos: { $sum: 1 } } },
  { $project: { _id: 0, continente: "$_id.continente", categoria: "$_id.categoria", numeroAutos: 1 } },
  { $sort: { continente: 1, categoria: 1 } }
]));

// 13. Desde fabricantes, contar sus autos; incluye fabricantes sin autos.
mostrar(13, "Total de autos por fabricante, incluyendo cero", fabricantes.aggregate([
  { $lookup: { from: "autos", localField: "_id", foreignField: "idMaker", as: "autosRegistrados" } },
  { $project: { _id: 0, fabricante: "$maker", nombreCompleto: "$fullName", numeroAutos: { $size: "$autosRegistrados" } } },
  { $sort: { numeroAutos: -1, fabricante: 1 } }
]));

// 14. Marcas del catalogo sin ningun auto registrado.
mostrar(14, "Modelos del catalogo sin autos registrados", fabricantes.aggregate([
  { $unwind: "$modelos" },
  { $lookup: { from: "autos", localField: "modelos.modelID", foreignField: "modelo.modelID", as: "autosDelModelo" } },
  { $match: { autosDelModelo: { $size: 0 } } },
  { $project: { _id: 0, modelID: "$modelos.modelID", marca: "$modelos.nombre", fabricante: "$maker" } },
  { $sort: { fabricante: 1, marca: 1 } }
]));

// 15. Cinco autos con mayor potencia y nombre completo del fabricante.
mostrar(15, "Cinco autos mas potentes", autos.aggregate([
  ...unirFabricante,
  { $sort: { "especificaciones.horsepower": -1, _id: 1 } },
  { $limit: 5 },
  { $project: { _id: 0, descripcion: 1, potenciaHp: "$especificaciones.horsepower", fabricante: "$fabricante.fullName" } }
]));

// 16. Tres autos con mas mpg por continente (solo continentes con autos).
mostrar(16, "Top 3 autos por mpg en cada continente", autos.aggregate([
  ...unirFabricante,
  { $setWindowFields: {
    partitionBy: "$fabricante.origen.continente",
    sortBy: { "especificaciones.mpg": -1, _id: 1 },
    output: { posicion: { $documentNumber: {} } }
  } },
  { $match: { posicion: { $lte: 3 } } },
  { $project: { _id: 0, continente: "$fabricante.origen.continente", posicion: 1, descripcion: 1, mpg: "$especificaciones.mpg" } },
  { $sort: { continente: 1, posicion: 1 } }
]));

// 17. Para fabricantes con mas de una marca, determinar la que tiene mas autos.
// En empates se elige la marca alfabeticamente menor.
mostrar(17, "Marca con mas autos de cada fabricante multimarca", fabricantes.aggregate([
  { $match: { "modelos.1": { $exists: true } } },
  { $unwind: "$modelos" },
  { $lookup: { from: "autos", localField: "modelos.modelID", foreignField: "modelo.modelID", as: "autosDeMarca" } },
  { $set: { numeroAutosMarca: { $size: "$autosDeMarca" } } },
  { $sort: { _id: 1, numeroAutosMarca: -1, "modelos.nombre": 1 } },
  { $group: { _id: "$_id", fabricante: { $first: "$maker" }, marca: { $first: "$modelos.nombre" }, numeroAutos: { $first: "$numeroAutosMarca" } } },
  { $project: { _id: 0, fabricante: 1, marca: 1, numeroAutos: 1 } },
  { $sort: { fabricante: 1 } }
]));

// 18. Porcentaje de autos por continente, incluyendo continentes con cero autos.
mostrar(18, "Porcentaje del total de autos por continente", continentes.aggregate([
  ...unirFabricantesPorContinente,
  { $lookup: { from: "autos", localField: "fabricantes._id", foreignField: "idMaker", as: "autosDelContinente" } },
  { $lookup: { from: "autos", pipeline: [{ $count: "total" }], as: "totalGeneral" } },
  { $set: { numeroAutos: { $size: "$autosDelContinente" }, totalAutos: { $ifNull: [{ $arrayElemAt: ["$totalGeneral.total", 0] }, 0] } } },
  { $project: { _id: 0, continente: 1, numeroAutos: 1, porcentaje: { $cond: [
    { $eq: ["$totalAutos", 0] }, 0,
    { $round: [{ $multiply: [{ $divide: ["$numeroAutos", "$totalAutos"] }, 100] }, 2] }
  ] } } },
  { $sort: { numeroAutos: -1, continente: 1 } }
]));

// 19. Cinco autos que mas superan el mpg promedio de su mismo numero de cilindros.
mostrar(19, "Cinco autos sobre el promedio de mpg de sus cilindros", autos.aggregate([
  { $setWindowFields: {
    partitionBy: "$especificaciones.cylinders",
    output: { promedioGrupo: { $avg: "$especificaciones.mpg", window: { documents: ["unbounded", "unbounded"] } } }
  } },
  { $set: { diferencia: { $subtract: ["$especificaciones.mpg", "$promedioGrupo"] } } },
  { $sort: { diferencia: -1, _id: 1 } },
  { $limit: 5 },
  { $project: { _id: 0, descripcion: 1, cilindros: "$especificaciones.cylinders", mpg: "$especificaciones.mpg", promedioMismosCilindros: { $round: ["$promedioGrupo", 2] }, diferenciaMpg: { $round: ["$diferencia", 2] } } }
]));

// 20. Por continente: autos, numero con 8+ cilindros y porcentaje con 1 decimal.
mostrar(20, "Autos con 8 o mas cilindros por continente", continentes.aggregate([
  ...unirFabricantesPorContinente,
  { $lookup: { from: "autos", localField: "fabricantes._id", foreignField: "idMaker", as: "autosDelContinente" } },
  { $set: {
    numeroAutos: { $size: "$autosDelContinente" },
    autos8OMasCilindros: { $size: { $filter: { input: "$autosDelContinente", as: "a", cond: { $gte: ["$$a.especificaciones.cylinders", 8] } } } }
  } },
  { $project: { _id: 0, continente: 1, numeroAutos: 1, autos8OMasCilindros: 1, porcentaje: { $cond: [
    { $eq: ["$numeroAutos", 0] }, 0,
    { $round: [{ $multiply: [{ $divide: ["$autos8OMasCilindros", "$numeroAutos"] }, 100] }, 1] }
  ] } } },
  { $sort: { continente: 1 } }
]));

// 21. Diez autos con mayor potencia por cada 1000 libras de peso, con pais.
mostrar(21, "Top 10 hp por 1000 lb", autos.aggregate([
  ...unirFabricante,
  { $match: { "especificaciones.weight": { $gt: 0 } } },
  { $set: { potenciaPor1000Lb: { $multiply: [{ $divide: ["$especificaciones.horsepower", "$especificaciones.weight"] }, 1000] } } },
  { $sort: { potenciaPor1000Lb: -1, _id: 1 } },
  { $limit: 10 },
  { $project: { _id: 0, descripcion: 1, pais: "$fabricante.origen.pais", potenciaHp: "$especificaciones.horsepower", pesoLb: "$especificaciones.weight", potenciaPor1000Lb: { $round: ["$potenciaPor1000Lb", 2] } } }
]));

// 22. Por fabricante, solo modelos con nombre distinto al del fabricante.
mostrar(22, "Modelos que no se llaman igual que su fabricante", fabricantes.aggregate([
  { $set: { modelosDistintos: { $filter: { input: "$modelos", as: "m", cond: { $ne: ["$$m.nombre", "$maker"] } } } } },
  { $match: { "modelosDistintos.0": { $exists: true } } },
  { $project: { _id: 0, fabricante: "$maker", modelos: "$modelosDistintos.nombre" } },
  { $sort: { fabricante: 1 } }
]));

// 23. Una sola consulta con $facet: por continente, por cilindros y estadisticas mpg.
mostrar(23, "Facet: autos por continente, por cilindros y estadisticas de mpg", autos.aggregate([
  { $facet: {
    porContinente: [
      ...unirFabricante,
      { $group: { _id: "$fabricante.origen.continente", numeroAutos: { $sum: 1 } } },
      { $project: { _id: 0, continente: "$_id", numeroAutos: 1 } },
      { $sort: { numeroAutos: -1, continente: 1 } }
    ],
    porCilindros: [
      { $group: { _id: "$especificaciones.cylinders", numeroAutos: { $sum: 1 } } },
      { $project: { _id: 0, cilindros: "$_id", numeroAutos: 1 } },
      { $sort: { cilindros: 1 } }
    ],
    estadisticasGlobalesMpg: [
      { $group: { _id: null, minimo: { $min: "$especificaciones.mpg" }, maximo: { $max: "$especificaciones.mpg" }, promedio: { $avg: "$especificaciones.mpg" } } },
      { $project: { _id: 0, minimo: 1, maximo: 1, promedio: { $round: ["$promedio", 2] } } }
    ]
  } }
]));

// 24. Ranking de autos alemanes por hp dentro de su pais. Mostrar top 5.
mostrar(24, "Cinco autos alemanes mejor posicionados por potencia", autos.aggregate([
  ...unirFabricante,
  { $match: { "fabricante.origen.pais": "germany" } },
  { $setWindowFields: {
    partitionBy: "$fabricante.origen.pais",
    sortBy: { "especificaciones.horsepower": -1, _id: 1 },
    output: { posicion: { $documentNumber: {} } }
  } },
  { $match: { posicion: { $lte: 5 } } },
  { $project: { _id: 0, posicion: 1, descripcion: 1, pais: "$fabricante.origen.pais", potenciaHp: "$especificaciones.horsepower" } },
  { $sort: { posicion: 1 } }
]));

// 25. Cada fabricante europeo y su auto con mas mpg. Incluye fabricantes sin autos.
mostrar(25, "Auto con mejor mpg de cada fabricante europeo", fabricantes.aggregate([
  ...normalizarFabricante,
  { $match: { "origen.continente": "europe" } },
  { $lookup: {
    from: "autos", localField: "_id", foreignField: "idMaker",
    pipeline: [
      { $sort: { "especificaciones.mpg": -1, _id: 1 } },
      { $limit: 1 },
      { $project: { _id: 0, descripcion: 1, mpg: "$especificaciones.mpg" } }
    ],
    as: "autoMasEficiente"
  } },
  { $unwind: { path: "$autoMasEficiente", preserveNullAndEmptyArrays: true } },
  { $project: { _id: 0, fabricante: "$maker", pais: "$origen.pais", auto: { $ifNull: ["$autoMasEficiente.descripcion", "Sin autos registrados"] }, mpg: { $ifNull: ["$autoMasEficiente.mpg", null] } } },
  { $sort: { fabricante: 1 } }
]));

