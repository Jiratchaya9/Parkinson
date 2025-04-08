import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'dart:convert';

void main() => runApp(const MyApp());

class MyApp extends StatelessWidget {
  const MyApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Video Frequency Analysis',
      theme: ThemeData(primarySwatch: Colors.blue),
      home: const PreScreeningPage(),
    );
  }
}

// ✅ **1. หน้าแบบสอบถาม (Pre-screening)**
class PreScreeningPage extends StatefulWidget {
  const PreScreeningPage({Key? key}) : super(key: key);

  @override
  _PreScreeningPageState createState() => _PreScreeningPageState();
}

class _PreScreeningPageState extends State<PreScreeningPage> {
  final List<String> questions = [
    "คุณมีอาการสั่นในขณะพักหรือไม่?",
    "คุณมีอาการแข็งเกร็งของกล้ามเนื้อหรือไม่?",
    "คุณรู้สึกว่าเคลื่อนไหวช้ากว่าปกติหรือไม่?",
    "คุณมีปัญหาในการทรงตัวหรือเดินหรือไม่?",
    "คุณมีอาการเปลี่ยนแปลงของลายมือหรือการเขียนหรือไม่?",
    "คุณเคยรู้สึกว่ากล้ามเนื้ออ่อนแรงผิดปกติหรือไม่?",
    "คุณมีอาการสีหน้าตึง ไม่แสดงอารมณ์หรือไม่?",
    "คุณมีปัญหาในการกลืนหรือพูดหรือไม่?",
    "คุณมีปัญหาการนอนหลับ เช่น นอนไม่หลับหรือฝันร้ายหรือไม่?",
    "คุณรู้สึกว่าอารมณ์เปลี่ยนแปลง เช่น ซึมเศร้าหรือวิตกกังวลมากขึ้นหรือไม่?",
  ];

  List<bool?> answers = List.filled(10, null);
  String riskMessage = "";

  void calculateRisk() {
    int riskScore = answers.where((answer) => answer == true).length;
    setState(() {
      riskMessage = riskScore > 5 ? "คุณอาจมีความเสี่ยงสูง โปรดปรึกษาแพทย์" : "คุณมีความเสี่ยงต่ำ";
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Pre-Screening")),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            const Text("กรุณาตอบแบบสอบถามเพื่อคัดกรองเบื้องต้น", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            Expanded(
              child: ListView.builder(
                itemCount: questions.length,
                itemBuilder: (context, index) {
                  return Card(
                    child: ListTile(
                      title: Text(questions[index]),
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Radio<bool>(
                            value: true,
                            groupValue: answers[index],
                            onChanged: (value) {
                              setState(() {
                                answers[index] = value;
                              });
                            },
                          ),
                          const Text("ใช่"),
                          Radio<bool>(
                            value: false,
                            groupValue: answers[index],
                            onChanged: (value) {
                              setState(() {
                                answers[index] = value;
                              });
                            },
                          ),
                          const Text("ไม่ใช่"),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
            Text(riskMessage, style: TextStyle(fontSize: 18, color: riskMessage.contains("ความเสี่ยงสูง") ? Colors.red : Colors.green)),
            ElevatedButton(
              onPressed: () {
                calculateRisk();
              },
              child: const Text("ประเมินผล"),
            ),
            ElevatedButton(
              onPressed: () {
                Navigator.push(context, MaterialPageRoute(builder: (context) => const UploadVideoPage()));
              },
              child: const Text("ถัดไป"),
            ),
          ],
        ),
      ),
    );
  }
}

// ✅ **2. หน้าอัปโหลดวิดีโอ**
class UploadVideoPage extends StatefulWidget {
  const UploadVideoPage({Key? key}) : super(key: key);

  @override
  _UploadVideoPageState createState() => _UploadVideoPageState();
}

class _UploadVideoPageState extends State<UploadVideoPage> {
  File? _videoFile;

  Future<void> _pickVideo() async {
    final pickedFile = await ImagePicker().pickVideo(source: ImageSource.gallery);
    if (pickedFile != null) {
      setState(() {
        _videoFile = File(pickedFile.path);
      });
    }
  }

  Future<void> _processVideo() async {
    if (_videoFile == null) return;
    
    var request = http.MultipartRequest(
      'POST',
      Uri.parse('http://172.20.10.9:5000/process_video'),
    );
    request.files.add(await http.MultipartFile.fromPath('video', _videoFile!.path));

    var response = await request.send();
    if (response.statusCode == 200) {
      var responseData = await response.stream.bytesToString();
      var jsonData = json.decode(responseData);
      double frequency = jsonData['frequency'];

      Navigator.push(context, MaterialPageRoute(builder: (context) => ResultPage(frequency: frequency)));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Upload Video")),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            ElevatedButton(onPressed: _pickVideo, child: const Text("Choose Video")),
            ElevatedButton(onPressed: _processVideo, child: const Text("Process Video")),
          ],
        ),
      ),
    );
  }
}