Here is the content of the PDF file formatted as a Markdown document.

```markdown
#  GenAI Task: Build an SHL Assessment Recommendation System [cite: 1]

##  Why are we asking you to do this assessment? [cite: 2]
 We use this assessment to evaluate the following core skills: [cite: 3]

1.   **Problem-Solving:** Ability to understand and synthesize the problem, decompose it into manageable components, and design a solution that is coherent, scalable, and meaningful. [cite: 4, 5]
2.  **Programming Skills:** Ability to write clean, effective, and reliable code to solve the problem.  This includes appropriate use of AI-assisted tools to accelerate development without compromising correctness or understanding. [cite: 6-8]
3.   **Context Engineering:** Ability to deeply understand the provided context, constraints, and data, and leverage them to produce solutions that are accurate, relevant, and well-aligned with the problem requirements. [cite: 9, 10]

###  Indicators of Unsuccessful Submissions [cite: 11]
 Based on our experience evaluating thousands of such assessments, candidates are unlikely to be successful if: [cite: 12, 13]
1.   **Insufficient programming skills and experience:** Core programming skills are not strong enough to implement a robust, maintainable, and extensible solution. [cite: 14, 15]
2.   **Vibe-coding is great but not replacement for foundations:** The solution relies on "vibe-coding" or trial-and-error without demonstrating a deep understanding of the problem, assumptions, and trade-offs. [cite: 16, 17]
3.   **Limited validation/testing rigor:** The solution is not tested across a sufficiently diverse set of inputs, edge cases, or realistic queries to demonstrate reliability and generalizability. [cite: 18, 19]

---

##  Brief overview of hiring process [cite: 20]
 Our hiring process consists of the following stages: [cite: 21]

1.   **Take-Home Assessment:** Evaluation of problem-solving ability, Gen AI programming skills, and context engineering. [cite: 22, 26]
2.   **First-Round Interview:** We take a deep-dive on your submission and do a technical discussion on different aspects i.e. reasoning behind design choices, and core programming fundamentals including live problem-solving and adaptation of solutions under changing constraints. [cite: 27, 28]
3.   **Second-Round Interview:** Discussion of experience, projects, and previous problem-solving experience. [cite: 29, 30]
4.   **Third-Round Interview:** Technical/Non-Technical discussion with hiring manager for understanding role alignment and motivation. [cite: 31, 32]

---

##  Problem Overview [cite: 33]
 Hiring managers and recruiters often struggle to find the right assessments for the roles that they are hiring for. [cite: 34]  The current system relies on keyword searches and filters, making the process time-consuming and inefficient. [cite: 35]

 **Your task is to build an intelligent recommendation system that simplifies this process.** [cite: 36]  Given a natural language query or a job description (JD) text or an URL (containing a JD), your application should return a list of relevant SHL assessments. [cite: 37]

 You can take a look at the data sources that you are going to work with here: [SHL Product Catalog](https://www.shl.com/solutions/products/product-catalog/) [cite: 38]

###  Your Task [cite: 39]
 Design and develop a web application that: [cite: 40]
1.   Takes a given natural language query or job description text URL. [cite: 42]
2.   Recommends minimum 5 (maximum 10) most relevant "individual test solutions" from the catalog in the tabular format. [cite: 45]
    *  *Note:* You need to ignore "Pre-packaged Job Solutions" category from this link. [cite: 46]
3.   Each recommendation needs to have at least the following attributes: [cite: 47]
    *  Assessment name [cite: 48]
    *  URL (as given in SHL's catalog) [cite: 49]

###  Datasets Given [cite: 50]
1.   **The actual data over which you need to build the recommendation engine:** [cite: 51]
    *  You need to crawl the assessment catalogue from the SHL website to be able to build this solution. [cite: 53]
    *  Make sure that there are at least **377 Individual Test Solutions** after crawling to the given website. [cite: 54]
    *  Build the recommendation system by leveraging this downloaded data. [cite: 55]
2.   **Validation Data:** [cite: 56]
    *  Once you have build your first solution you can use train data provided to validate and iterate over it. [cite: 56]
    * **Labelled Train set:** This contains a set of 10 queries labeled by humans, most relevant assessments from the catalog.  This can be used to iterate over your prompts, improve your pipeline etc. [cite: 58-60]
3.   **Test Data:** [cite: 61]
    *  **Unlabeled test set:** This dataset contains a set of 9 queries - on which you have to generate and submit predictions. [cite: 64]

###  Submission Materials [cite: 65]
 You need to submit the following items: [cite: 66]

1.   **API Endpoint URL:** Can be queried using a query or piece of text and returns result in JSON (See Appendix 2). [cite: 68]
2.   **GitHub Code URL:** URL of the complete code (public or private shared with us), including experiments and evaluation. [cite: 69, 77]
3.   **Web Application Frontend URL:** To test the application. [cite: 70]
4.  **2-Page Document:** Outlining your approach, efforts to optimize performance, initial results, and improvements.  Write concisely. [cite: 71-73]
5.   **1 CSV File:** Contains predictions on the given unlabeled test set (Format in Appendix 3). [cite: 74, 75]

 **Vital Checks:** Ensure the API is functional, code is accessible, and the CSV is in the correct format. [cite: 77, 78]

---

##  Evaluation Criteria (Core Logic) [cite: 79]

###  1. Solution Approach [cite: 81]
 We expect a clear and implementable strategy that directly addresses the problem statement. [cite: 83]

 **Data Pipeline:** [cite: 84]
*  A well-defined pipeline connecting data ingestion, retrieval, and recommendation. [cite: 86]
*  Logical flow between components (data → embedding search → recommendation). [cite: 87]
*  Modular, reproducible, and maintainable code structure. [cite: 88]
*  Implementation of a data ingestion pipeline that scrapes or retrieves SHL product information. [cite: 90]
*  Clean parsing and structuring of product data (titles, categories, URLs, etc.). [cite: 91]
*  Use of efficient storage and retrieval mechanisms e.g., embeddings or vector databases. [cite: 92]
*  *Rejection Criteria:* Solutions built without scraping and storing SHL product catalogue from the website will be rejected. [cite: 93]

 **Technology Stack & LLM Integration:** [cite: 94]
*  Use of modern LLM-based or retrieval-augmented techniques for query understanding or recommendation generation. [cite: 96]
*  Justifiable use of frameworks (Langfuse, LangChain, LlamaIndex, etc.). [cite: 97]
*  *Rejection Criteria:* Solutions without clear LLM or retrieval-based integration will be rejected. [cite: 99]

 **Evaluation:** [cite: 98]
*  Implementation of evaluation methods to measure system accuracy and effectiveness applied to the right stages (retrieval and final recommendation). [cite: 101, 102]
*  Use the provided train data to evaluate and iterate. [cite: 103]
*  *Rejection Criteria:* Solutions lacking measurable evaluation will be rejected. [cite: 104]

###  2. Performance and Relevance [cite: 105]
*  **Recommendation Accuracy:** Measured by the **Mean Recall@10** against the provided test set. [cite: 106]
*  **Recommendation Balance:** The system must intelligently balance recommendations when a query spans multiple domains (e.g., behavioral and technical skills). [cite: 107-109]

 **Example Scenario:** [cite: 110]
*  *Query:* "Need a Java developer who is good in collaborating with external teams and stakeholders." [cite: 111]
*  *Expected Outcome:* Balanced set of assessments including hard skills (Test Type K - Knowledge & Skills) and soft skills (Test Type P - Personality & Behavior). [cite: 112]

 **Test Types:** [cite: 114]
| Code | Description |
| :--- | :--- |
| **A** |  Ability & Aptitude [cite: 116] |
| **B** |  Biodata & Situational Judgement [cite: 117] |
| **C** |  Competencies [cite: 118] |
| **D** |  Development & 360 [cite: 119] |
| **E** |  Assessment Exercises [cite: 120] |
| **K** |  Knowledge & Skills [cite: 121] |
| **P** |  Personality & Behavior [cite: 122] |
| **S** |  Simulations [cite: 123] |

###  Resources [cite: 124]
*  **LLMs/Gemini Free APIs:** [Google AI Pricing](https://ai.google.dev/gemini-api/docs/pricing) [cite: 128]
*  **Cloud deployment platforms:** [Free Tier Comparison](https://github.com/cloudcommunity/Cloud-Free-Tier-Comparison) [cite: 130]

---

##  Index: Metrics to compute accuracy [cite: 131]

 **Mean Recall@K** [cite: 133]
 This metric measures how many of the relevant assessments were retrieved in the top K recommendations, averaged across all test queries. [cite: 134]

 $$Recall@K = \frac{\text{Number of relevant assessments in top K}}{\text{Total relevant assessments for the query}}$$ [cite: 136]

 $$MeanRecall@K = \frac{1}{N} \sum_{i=1}^{N} Recall@K_i$$ [cite: 139]

 where $N$ is the total number of test queries. [cite: 140]

---

##  Appendix 1: Sample Queries [cite: 141]
*  I am hiring for Java developers who can also collaborate effectively with my business teams. [cite: 143]
*  Looking to hire mid-level professionals who are proficient in Python, SQL and Java Script. [cite: 144]
*  Here is a JD text, can you recommend some assessment that can help me screen applications. [cite: 145]
*  I am hiring for an analyst and wants applications to screen using Cognitive and personality tests. [cite: 146]

---

##  Appendix 2: API Structure & Endpoints [cite: 147]

 Your API must implement the endpoints described below exactly as specified. [cite: 149]

 **Base Requirements:** [cite: 150]
*  Accessible via HTTP/HTTPS [cite: 151]
*  Proper HTTP status codes [cite: 152]
*  JSON format for all data exchanges [cite: 153]

###  1. Health Check Endpoint [cite: 155]
**Request:**
*  **Method:** `GET` [cite: 157]
*  **Path:** `<YOUR-BASE-URL>/health` [cite: 158]

**Response:**
```json
{
  "status": "healthy"
}

```



2. Assessment Recommendation Endpoint 

Accepts a job description or Natural language query and returns recommended relevant assessments (At most 10, minimum 1).

**Request:**

* 
**Method:** `POST` 


* 
**Path:** `<YOUR-BASE-URL>/recommend` 


* 
**Content-Type:** `application/json` 



```json
{
  "query": "JD/query in string"
}

```



**Response:**

* 
**Content-Type:** `application/json` 


* 
**Status Code:** `200 OK` (if successful) 



```json
{
  "recommended_assessments": [
    {
      "url": "Valid URL in string",
      "adaptive_support": "Yes/No",
      "description": "Description in string",
      "duration": 60,
      "remote_support": "Yes/No",
      "test_type": ["List of string"]
    }
  ]
}

```



**Response Fields Explanation:** 

| Field | Type | Description |
| --- | --- | --- |
| `url` | String | Valid URL to the assessment resource |
| `name` | String | Name of the assessment |
| `adaptive_support` | String | Either "Yes" or "No" indicating if the assessment supports adaptive testing |
| `description` | String | Detailed description of the assessment |
| `duration` | Integer | Duration of the assessment in minutes |
| `remote_support` | String | Either "Yes" or "No" indicating if the assessment can be taken remotely |
| `test type` | Array of Strings | Categories or types of the assessment |

**Example Response:** 

```json
{
  "recommended_assessments": [
    {
      "url": "[https://www.shl.com/solutions/products/product-catalog/view/python-new/](https://www.shl.com/solutions/products/product-catalog/view/python-new/)",
      "name": "Python (New)",
      "adaptive_support": "No",
      "description": "Multi-choice test that measures the knowledge of Python programming, databases, modules and library...",
      "duration": 11,
      "remote_support": "Yes",
      "test_type": ["Knowledge & Skills"]
    },
    {
      "url": "[https://www.shl.com/solutions/products/product-catalog/view/technology-professional-8-8-job-focused-assessment/](https://www.shl.com/solutions/products/product-catalog/view/technology-professional-8-8-job-focused-assessment/)",
      "name": "Technology Professional 8.0 Job Focused Assessment",
      "adaptive_support": "No",
      "description": "The Technology Job Focused Assessment assesses key behavioral attributes required for success in fast-paced roles.",
      "duration": 16,
      "remote_support": "Yes",
      "test_type": ["Competencies", "Personality & Behaviour"]
    }
  ]
}

```



---

Appendix 3: Submission Data Format 

The CSV file should be submitted in the format below. 

| Query | Assessment_url |
| --- | --- |
| Query 1 | Recommendation 1 (URL) |
| Query 1 | Recommendation 2 (URL) |
| Query 1 | Recommendation 3 (URL) |
| Query 2 | Recommendation 1 |



*Note: The submission should be in exactly the above format, if the above format is not followed then you will not be scored.* 

```

```