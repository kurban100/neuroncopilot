from neo4j import GraphDatabase

class KnowledgeGraph:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="Node_Cool11"):
        """Initializes the connection to Neo4j Desktop."""
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        """Closes the connection pool."""
        self.driver.close()

    def query(self, cypher_query, parameters=None):
        """Executes a Cypher query and returns the records."""
        with self.driver.session() as session:
            result = session.run(cypher_query, parameters)
            return [record for record in result]

    def create_constraints(self):
        """Sets up constraints to ensure uniqueness and speed up queries."""
        constraints = [
            "CREATE CONSTRAINT unique_concept_name IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT unique_student_id IF NOT EXISTS FOR (s:Student) REQUIRE s.id IS UNIQUE"
        ]
        for constraint in constraints:
            self.query(constraint)
        print("✓ Database constraints validated.")
        # src/graph/knowledge_graph.py


    #Method 1 concept based recommendations
    def get_next_concepts(self, current_concept):
        """Fetches concepts connected to the current concept."""
        query = """
        MATCH (c)-[:REQUIRES]-(next)
        WHERE c.name = $name
        RETURN next.name AS concept_name
        """
        with self.driver.session() as session:
            result = session.run(query, name=current_concept)
            return [record["concept_name"] for record in result]

    def get_next_recommendations(self, student_id):
        """Get personalized recommendations based on student progress"""
        print(f"\n>>> START get_next_recommendations for {student_id}")
    
        query = """
        MATCH (s:Student {id: $student_id})-[:MASTERED]->(mastered:Concept)
        MATCH (next:Concept)-[:REQUIRES]->(mastered)
        WHERE NOT (s)-[:MASTERED]->(next)
        RETURN DISTINCT next.name AS name,
            next.difficulty AS difficulty,
            count(mastered) AS prerequisites_met
        ORDER BY prerequisites_met DESC, next.difficulty ASC
        LIMIT 5
        """
    
        with self.driver.session() as session:
            result = session.run(query, student_id=student_id)
            records = result.data()  # Get all as list
            print(f">>> Query returned {len(records)} records")
            print(f">>> Records: {records}")
            return records
    
    def initialize_ml_graph(self):  # ← 4 spaces (next method)
        """Seeds the ML Knowledge Graph..."""
        
        # 1. Create Concepts safely using MERGE
        concepts_query = """
        // Fundamental Concepts
         
        MERGE (c2:Concept {name: "Linear Algebra"}) ON CREATE SET c2.difficulty = 1, c2.description = "Vectors, matrices, and operations"
        MERGE (c3:Concept {name: "Statistics Basics"}) ON CREATE SET c3.difficulty = 1, c3.description = "Mean, variance, distributions"

        // Intermediate Concepts  
        MERGE (c4:Concept {name: "Gradient Descent"}) ON CREATE SET c4.difficulty = 2, c4.description = "Optimization algorithm"
        MERGE (c5:Concept {name: "Cost Functions"}) ON CREATE SET c5.difficulty = 2, c5.description = "Measuring model error"
        MERGE (c6:Concept {name: "Linear Regression"}) ON CREATE SET c6.difficulty = 2, c6.description = "Predicting continuous values"
        MERGE (c7:Concept {name: "Logistic Regression"}) ON CREATE SET c7.difficulty = 3, c7.description = "Binary classification"

        // Advanced Concepts
        MERGE (c8:Concept {name: "Neural Networks"}) ON CREATE SET c8.difficulty = 4, c8.description = "Multi-layer learning models"
        MERGE (c9:Concept {name: "Backpropagation"}) ON CREATE SET c9.difficulty = 4, c9.description = "Computing gradients efficiently"
        MERGE (c10:Concept {name: "Regularization"}) ON CREATE SET c10.difficulty = 3, c10.description = "Preventing overfitting"
        MERGE (c11:Concept {name: "Convolutional Networks"}) ON CREATE SET c11.difficulty = 5, c11.description = "Image processing networks"
        """
        self.query(concepts_query)

        # 2. Build prerequisite relationships safely using MERGE
        relationships_query = """
        MATCH (gd:Concept {name: "Gradient Descent"}), (d:Concept {name: "Derivatives"}) MERGE (gd)-[:REQUIRES]->(d)
        MATCH (gd:Concept {name: "Gradient Descent"}), (la:Concept {name: "Linear Algebra"}) MERGE (gd)-[:REQUIRES]->(la)
        MATCH (lr:Concept {name: "Linear Regression"}), (gd:Concept {name: "Gradient Descent"}) MERGE (lr)-[:REQUIRES]->(gd)
        MATCH (lr:Concept {name: "Linear Regression"}), (cf:Concept {name: "Cost Functions"}) MERGE (lr)-[:REQUIRES]->(cf)
        MATCH (log:Concept {name: "Logistic Regression"}), (lr:Concept {name: "Linear Regression"}) MERGE (log)-[:REQUIRES]->(lr)
        MATCH (nn:Concept {name: "Neural Networks"}), (log:Concept {name: "Logistic Regression"}) MERGE (nn)-[:REQUIRES]->(log)
        MATCH (bp:Concept {name: "Backpropagation"}), (nn:Concept {name: "Neural Networks"}) MERGE (bp)-[:REQUIRES]->(nn)
        MATCH (reg:Concept {name: "Regularization"}), (lr:Concept {name: "Linear Regression"}) MERGE (reg)-[:REQUIRES]->(lr)
        MATCH (cnn:Concept {name: "Convolutional Networks"}), (nn:Concept {name: "Neural Networks"}) MERGE (cnn)-[:REQUIRES]->(nn)
        """
        self.query(relationships_query)

        # 3. Create test student profiles and progress states
        student_query = """
        MERGE (s:Student {id: "student_001"})
        ON CREATE SET s.name = "Test Student", s.level = 2

        WITH s
        MATCH (c1:Concept {name: "Derivatives"}) 
        MERGE (s)-[m1:MASTERED]->(c1) ON CREATE SET m1.score = 0.95, m1.date = datetime()

        WITH s
        MATCH (c2:Concept {name: "Linear Algebra"}) 
        MERGE (s)-[m2:MASTERED]->(c2) ON CREATE SET m2.score = 0.88, m2.date = datetime()

        WITH s
        MATCH (c3:Concept {name: "Statistics Basics"}) 
        MERGE (s)-[m3:MASTERED]->(c3) ON CREATE SET m3.score = 0.92, m3.date = datetime()
        """
        self.query(student_query)
        print("✓ ML Knowledge Graph successfully seeded and updated!")