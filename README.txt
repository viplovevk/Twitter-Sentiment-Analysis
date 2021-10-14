Loading of Keras deep learning model from Jupyter to HTML

Steps:
-Copy all files to a single working directory
-Ran using Anaconda3 command prompt
-cd anaconda3 to working directory
-new2.py templates/index.html
-open URL in your browser with the displayed URL in prompt (http://127.0.0.1:5000/)
*Do not query until next step is done*

Socket listener:
Open Socketrun3.ipynb in jupyter notebook and run the first cell (should see 'listening on port num xxxx') 

After listening, query the html page with a keyword, the anaconda prompt for the new2.py app should display the working messages
of retrieving spark information (40 second timer set so far).

-----------------------------------------------------------------------------------------------------------------------------

Explaination:
-Dataset is used to prepare a NLP tokenizer, tokenizer is saved with this line in last cell
joblib.dump(tokenizer, "data_tokenizer.joblib")

-Model is trained in Jupyter, saved with this line
model.save("model.h5")

-Model and tokenizer will be saved in Jupyter's working directory, after saving extract the Model.h5 file
and data_tokenizer.joblib file into the working directory for steps above

-input in HTML form needs to be transformed into the tokenized vector before feeding into the loaded DL model
