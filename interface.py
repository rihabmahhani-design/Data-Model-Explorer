import streamlit as st
import pandas as pd
from neo4j import GraphDatabase

# --- 1. CONFIGURATION & STYLE ---
st.set_page_config(page_title="Data Model Explorer", layout="wide")

# Style CSS épuré pour l'interface
st.markdown("""
<style>
    .main-title { font-size: 42px; font-weight: bold; text-align: left; color: #333; margin-bottom: 20px; }
    .label-display { font-weight: bold; color: #333; margin-top: 15px; font-size: 18px; }
    .value-display { margin-bottom: 15px; padding: 8px; background-color: #f8f9fa; border-radius: 5px; border: 1px solid #eee; min-height: 38px; }
    
    /* Style pour faire ressembler la sélection à des boutons d'onglets personnalisés */
    div.stRadioButton > div {
        flex-direction: row;
    }
    div.stRadioButton > div > label {
        background-color: #f1f3f5;
        padding: 10px 30px;
        border-radius: 4px;
        border: 1px solid #ced4da;
        margin-right: 10px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# --- 2. CONNEXION NEO4J ---
URI = "neo4j+s://415e98bb.databases.neo4j.io " #URI = "bolt://localhost:7687"
AUTH = ("neo4j", "Neo4jTest")

@st.cache_resource
def get_neo4j_driver():
    return GraphDatabase.driver(URI, auth=AUTH)

try:
    driver = get_neo4j_driver()
except Exception as e:
    st.error(f"Erreur de connexion à Neo4j : {e}")


# --- 3. FONCTIONS NEO4J (LOGIQUE CORRIGÉE) ---

# Fonction de recherche pour l'onglet "Search: Class"
def get_class_details(name):
    with driver.session() as session:
        query = """
        MATCH (c:Class) WHERE c.Class_Name =~ ('(?i)' + $name)
        
        // Récupération des super-classes (classes mères)
        OPTIONAL MATCH (c)-[:IS_SUBCLASS_OF]->(parent:Class)
        
        // Récupération des sous-classes (classes filles)
        OPTIONAL MATCH (child:Class)-[:IS_SUBCLASS_OF]->(c)
        
        // Récupération de tous les attributs (directs ou hérités)
        OPTIONAL MATCH (c)-[r_attr:HAS_ATTRIBUTE|INHERITS_ATTRIBUTE]->(attr:Attribute)
        
        // Récupération des associations personnalisées (excluant la hiérarchie et les attributs)
        OPTIONAL MATCH (c)-[r]->(other)
        WHERE NOT type(r) IN ['HAS_ATTRIBUTE', 'INHERITS_ATTRIBUTE', 'IS_SUBCLASS_OF']
        
        RETURN c, 
               collect(distinct parent.Class_Name) as super_classes,
               collect(distinct child.Class_Name) as sub_classes,
               collect(distinct attr.Attribute_Name) as attributes,
               collect(distinct type(r) + " -> " + coalesce(other.Class_Name, other.Attribute_Name)) as associations
        """
        return session.run(query, name=name).single()

# Fonction de recherche pour l'onglet "Search: Attribute"
def get_attribute_details(name):
    with driver.session() as session:
        query = """
        MATCH (a:Attribute) WHERE a.Attribute_Name =~ ('(?i)' + $name)
        
        // Trouver la ou les classes propriétaires directes
        OPTIONAL MATCH (c:Class)-[:HAS_ATTRIBUTE]->(a)
        
        // Trouver les associations de l'onglet Relationships qui pointent vers cet attribut
        OPTIONAL MATCH (source:Class)-[r]->(a)
        WHERE NOT type(r) IN ['HAS_ATTRIBUTE', 'INHERITS_ATTRIBUTE']
        
        RETURN a, 
               collect(distinct c.Class_Name) as class_names,
               collect(distinct type(r) + " (from " + source.Class_Name + ")") as associations
        """
        return session.run(query, name=name).single()


# ==============================================================================
# --- 4. INTERFACE UTILISATEUR (UI) ---
# ==============================================================================

# Titre de l'application
st.markdown('<div class="main-title">Data Model Explorer</div>', unsafe_allow_html=True)
st.markdown("---")

# Sélection du mode de recherche : Class ou Attribute
search_mode = st.radio(
    "", 
    ["Search: Class", "Search: Attribute"], 
    horizontal=True,
    label_visibility="collapsed"
)

st.markdown("---")

# Barre de recherche textuelle
search_query = st.text_input("Search:", placeholder=f"Type a {search_mode.split(': ')[1]} name...")


# ==============================================================================
# --- VUE 1 : SEARCH CLASS ---
# ==============================================================================
if search_mode == "Search: Class":
    if search_query:
        result = get_class_details(search_query)
        
        if result:
            cls_node = result['c']
            super_classes = ", ".join(result['super_classes']) if result['super_classes'] else "nan"
            sub_classes = ", ".join(result['sub_classes']) if result['sub_classes'] else "nan"
            attrs = result['attributes']
            associations = result['associations']
            
            # Affichage des champs textuels de la classe
            st.markdown('<div class="label-display">Class Name:</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="value-display">{cls_node.get("Class_Name", "nan")}</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="label-display">Super Class Name:</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="value-display">{super_classes}</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="label-display">Sub Class Name:</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="value-display">{sub_classes}</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="label-display">URI:</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="value-display">{cls_node.get("Class_URI", "nan")}</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="label-display">Description:</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="value-display">{cls_node.get("Description", "No description")}</div>', unsafe_allow_html=True)
            
            # Tableau des Attributs
            st.markdown('<div class="label-display">Attributes:</div>', unsafe_allow_html=True)
            if attrs:
                df_attrs = pd.DataFrame(attrs, columns=["Attribute Name"])
                st.table(df_attrs)
            else:
                st.info("No attributes linked to this class.")
                
            # Section Association
            st.markdown('<div class="label-display">Association:</div>', unsafe_allow_html=True)
            if associations:
                for assoc in associations:
                    st.write(f"- {assoc}")
            else:
                st.write("nan")
        else:
            st.error("Class not found.")


# ==============================================================================
# --- VUE 2 : SEARCH ATTRIBUTE ---
# ==============================================================================
elif search_mode == "Search: Attribute":
    if search_query:
        result = get_attribute_details(search_query)
        
        if result:
            attr_node = result['a']
            class_names = ", ".join(result['class_names']) if result['class_names'] else "nan"
            associations = result['associations']
            
            # Affichage des métadonnées de l'attribut
            st.markdown('<div class="label-display">Attribute Name:</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="value-display">{attr_node.get("Attribute_Name", "nan")}</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="label-display">Attribute URI:</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="value-display">{attr_node.get("Attribute_URI", "nan")}</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="label-display">Discipline:</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="value-display">{attr_node.get("Discipline", "nan")}</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="label-display">Class Name Association (Domains):</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="value-display">{class_names}</div>', unsafe_allow_html=True)
            
            # Section Tableau des Associations
            st.markdown('<div class="label-display">Associations:</div>', unsafe_allow_html=True)
            
            if associations:
                table_data = {
                    "Attribute Name": [attr_node.get("Attribute_Name", "nan")] * len(associations),
                    "Associations": associations
                }
                df_assoc = pd.DataFrame(table_data)
                st.table(df_assoc)
            else:
                st.write("nan")
            
        else:
            st.error("Attribute not found.")