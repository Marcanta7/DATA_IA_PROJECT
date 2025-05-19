# NutriBot 🥗🤖

## Descripción

**NutriBot** es un agente conversacional desarrollado con **LangGraph** que genera recomendaciones de dietas saludables de forma personalizada. Utiliza una base de datos de planes nutricionales extraídos de PDFs, vectorizados con **Weaviate**, y optimiza la propuesta según intolerancias alimentarias y precios actualizados de ingredientes, consultando una base en **BigQuery**.  
Además, utiliza **Firebase** para almacenar de forma persistente el contexto de las conversaciones con los usuarios, asegurando una experiencia continua y personalizada.

---

## El Problema 🎯

Los usuarios interesados en llevar una dieta saludable enfrentan múltiples barreras:

- Dificultad para encontrar planes alimenticios confiables y adaptados  
- Falta de personalización respecto a intolerancias y preferencias  
- Desconocimiento de los costos reales de seguir una dieta  
- Recomendaciones genéricas sin validación nutricional  
- Poca integración entre contenido nutricional y contexto personal  

---

## Características Principales 💡

### Agente Inteligente con LangGraph

- Flujos conversacionales controlados por estado  
- Memoria persistente de intolerancias y preferencias  
- Toma de decisiones basada en herramientas especializadas (tools)

### Contexto Persistente con Firebase

- Almacenamiento del historial de conversación del usuario  
- Recuperación eficiente del estado conversacional entre sesiones  
- Escalabilidad y sincronización en tiempo real  

### Repositorio de Dietas Vectorizado

- Extracción y vectorización de contenido desde PDFs nutricionales  
- Búsqueda semántica precisa con Weaviate  
- Filtros automáticos según intolerancias alimentarias  

### Consulta de Precios en Tiempo Real

- Integración con **BigQuery** para obtener precios de ingredientes  
- Evaluación económica de cada dieta recomendada  
- Determinación de precios con búsqueda contextual de alimentos 

---

## Arquitectura 🔧

NutriBot se construye sobre una arquitectura modular e inteligente:

- **LangGraph**: Control de flujo y gestión del agente  
- **Weaviate**: Vectorización semántica y recuperación de dietas  
- **BigQuery**: Almacenamiento de datos de precios por región y temporalidad  
- **Firebase**: Persistencia de conversaciones y estado del usuario  
- **Tools personalizadas**: Manejo de preferencias, intolerancias y cotización  

---

## Beneficios 📈

### Para Usuarios

- Planes de alimentación realmente personalizados  
- Adaptación a necesidades médicas y preferencias personales  
- Muestra real del presupuesto alimenticio  

### Para el Ecosistema de Salud

- Herramienta de asistencia alimentaria preventiva  
- Promoción de hábitos saludables con base científica  
- Escalabilidad hacia distintos perfiles y regiones  

---

## Equipo 👥
  
- **Pablo Arnau** 
- **Marc Cantero**
- **Pau Jorques**
- **Ignacio Martínez**
- **Jairo Navarro**
- **Joaquín Zapata**

 

---

