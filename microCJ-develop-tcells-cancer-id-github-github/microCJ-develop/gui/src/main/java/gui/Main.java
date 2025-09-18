/*
Copyright 2019 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
package gui;

import javafx.application.Application;
import javafx.fxml.FXMLLoader;
import javafx.scene.Scene;
import javafx.scene.layout.BorderPane;
import javafx.scene.layout.VBox;
import javafx.scene.paint.Color;
import javafx.stage.Stage;

import java.io.File;
import java.io.IOException;

public class Main extends Application {

	@Override
	public void start(Stage primaryStage) {
		//cleanup();
		try {
			FXMLLoader fxmlLoader = new FXMLLoader(getClass().getResource("/fxml/start.fxml"));
			VBox root = fxmlLoader.load();
			primaryStage.setTitle("microCJ");
			Scene scene = new Scene(root, 400, 400, true);
			scene.getStylesheets().add(getClass().getResource("/css/bootstrap3.css").toExternalForm());
			scene.setFill(Color.WHITE);
			primaryStage.setScene(scene);
			primaryStage.setMaximized(true);
			primaryStage.show();
		}

		catch (IOException ioe) {
			// TODO Auto-generated catch block
			ioe.printStackTrace();
		}
	}

	private void cleanup() {
		File snapsDir = new File("snaps/");
		System.out.println(snapsDir);
		System.out.println(snapsDir.exists());

		for(File file: new File("snaps/").listFiles()) {
			if (!file.isDirectory()) file.delete();
		}
	}

	@Override
	public void stop() throws Exception {
		super.stop();
		System.exit(0);
	}

	/**
	 * The main() method is ignored in correctly deployed JavaFX application.
	 * main() serves only as fallback in case the application can not be
	 * launched through deployment artifacts, e.g., in IDEs with limited FX
	 * support. NetBeans ignores main().
	 *
	 * @param args the command line arguments
	 */
	public static void main(String[] args) {
		launch(args);
	}
}