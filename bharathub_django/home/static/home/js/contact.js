// NOTE: Contact ఫారమ్ ఇప్పుడు నిజమైన Django <form method="post"> ద్వారా
// నేరుగా home/views.py లోని ContactView.post() కి సబ్మిట్ అవుతుంది
// (CSRF token + ContactForm సర్వర్-సైడ్ వాలిడేషన్ తో). ఇంతకుముందు ఇక్కడ
// ఉన్న submitContact() JS ఫంక్షన్ పాత ఫీల్డ్ IDs (cName/cEmail/...) ని
// రిఫర్ చేసేది -- ఆ IDs ఇప్పుడు లేవు (ఫారమ్ Django-రెండర్డ్ ఫీల్డ్స్
// వాడుతుంది), కాబట్టి ఆ ఫంక్షన్ dead/broken code -- తీసివేశాం.
