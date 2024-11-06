/**
 * SPDX-FileCopyrightText: 2023 Steven Hartley
 *
 * See the NOTICE file(s) distributed with this work for additional
 * information regarding copyright ownership.
 *
 * This program and the accompanying materials are made available under the
 * terms of the Apache License Version 2.0 which is available at
 * https://www.apache.org/licenses/LICENSE-2.0
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package com.example.cottage2;

import android.content.Intent;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.RadioButton;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;

import com.example.cottage2.data.Mode;
import com.example.cottage2.data.Pressures;
import com.example.cottage2.data.Temperatures;
import com.google.android.gms.tasks.OnCompleteListener;
import com.google.android.gms.tasks.Task;
import com.google.firebase.FirebaseApp;
import com.google.firebase.appcheck.FirebaseAppCheck;
import com.google.firebase.appcheck.debug.DebugAppCheckProviderFactory;
import com.google.firebase.auth.AuthResult;
import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.FirebaseUser;
import com.google.firebase.database.DataSnapshot;
import com.google.firebase.database.DatabaseError;
import com.google.firebase.database.DatabaseReference;
import com.google.firebase.database.FirebaseDatabase;
import com.google.firebase.database.ValueEventListener;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.Optional;

public class MainActivity extends AppCompatActivity {
    // creating a variable for
    // our Firebase Database.
    FirebaseDatabase firebaseDatabase;

    private static final String USERNAME = "steven@orangepeel.ca"; // firebase email address
    private static final String PASSWORD = "PUT YOUR OWN PASSWORD HERE"; // stored in 1password

    // creating a variable for our
    // Database Reference for Firebase.
    DatabaseReference databaseReference;

    // variable for Text view.
    private TextView tvTimestamp;
    private TextView tvSystem;
    private TextView tvTemperatures;
    private TextView tvPressures;
    private TextView tvOverrideMode;
    private TextView tvAccountEmail;

    private CheckBox tvSignedIn;

    private RadioButton zone1;
    private RadioButton zone2;
    private RadioButton zone3;
    private RadioButton zone4;
    private RadioButton zone5;
    private RadioButton zone6;
    private RadioButton zone7;
    private RadioButton zone8;

    private Button logsButton;

    private Button override;

    private FirebaseAuth mAuth;

    @Override
    public void onStart() {
        super.onStart();
        // Check if user is signed in (non-null) and update UI accordingly.
        FirebaseUser currentUser = mAuth.getCurrentUser();
        if(currentUser == null) {
            signIn();
        } else {
            updateUI(currentUser);
        }
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        logsButton = (Button) findViewById(R.id.idLogButton);
        logsButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                Intent intent = new Intent(getApplicationContext(), LogsActivity.class);
                startActivity(intent);
            }
        });

        override = (Button) findViewById(R.id.idOverride);
        override.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                Intent intent = new Intent(getApplicationContext(), OverrideActivity.class);
                startActivity(intent);
            }
        });
        // Initialize Firebase Auth
        mAuth = FirebaseAuth.getInstance();

        FirebaseApp.initializeApp(/*context=*/ this);
        FirebaseAppCheck firebaseAppCheck = FirebaseAppCheck.getInstance();
        firebaseAppCheck.installAppCheckProviderFactory(
                DebugAppCheckProviderFactory.getInstance());

        firebaseDatabase = FirebaseDatabase.getInstance();

        // below line is used to get
        // reference for our database.
        databaseReference = firebaseDatabase.getReference("/cottage/geo");


        // initializing our object class variable.
        tvTimestamp = findViewById(R.id.idTimestamp);
        tvSystem = findViewById(R.id.idSystem);
        tvTemperatures = findViewById(R.id.idTemperatures);
        tvPressures = findViewById(R.id.idPressures);
        zone1 = (RadioButton)findViewById(R.id.radioButton1);
        tvOverrideMode = findViewById(R.id.idOverrideMode);
        zone2 = (RadioButton)findViewById(R.id.radioButton2);
        zone3 = (RadioButton)findViewById(R.id.radioButton3);
        zone4 = (RadioButton)findViewById(R.id.radioButton4);
        zone5 = (RadioButton)findViewById(R.id.radioButton5);
        zone6 = (RadioButton)findViewById(R.id.radioButton6);
        zone7 = (RadioButton)findViewById(R.id.radioButton7);
        zone8 = (RadioButton)findViewById(R.id.radioButton8);
        tvAccountEmail = findViewById(R.id.idAccountName);
        tvSignedIn = findViewById(R.id.idSignedIn);

        // calling method
        // for getting data.
        getdata();
    }

    private void getdata() {

        // calling add value event listener method
        // for getting the values from database.
        databaseReference.addValueEventListener(new ValueEventListener() {
            @Override
            public void onDataChange(@NonNull DataSnapshot snapshot) {
                // this method is call to get the realtime
                // updates in the data.
                // this method is called when the data is
                // changed in our Firebase console.
                // below line is for getting the data from
                // snapshot of our database.

                try {
                    String current = snapshot.child("current").getValue(String.class);
                    Integer override = snapshot.child("override").getValue(Integer.class);
                    if (override != null) {
                        tvOverrideMode.setText(Mode.fromValue(override).orElse(Mode.AUTOMATIC).getName());
                    } else {
                        tvOverrideMode.setText("Not Set");
                    }
                    JSONObject json = new JSONObject(current);

                    StringBuilder str = new StringBuilder();

                    Optional<Mode> mode = Mode.fromValue(Integer.valueOf(json.get("m").toString()));
                    if (mode.isPresent()) {
                        tvSystem.setText(mode.get().getName());
                    }

                    tvTimestamp.setText(json.get("time").toString());
                    //tvUpTime.setText(json.get("uptime").toString());
                    //tvLastError.setText(json.get("lasterror").toString());

                    JSONArray temps = json.getJSONArray("t");

                    JSONArray zones = json.getJSONArray("z");

                    zone1.setChecked(zones.getInt(0) == 1);
                    zone2.setChecked(zones.getInt(1) == 1);
                    zone3.setChecked(zones.getInt(2) == 1);
                    zone4.setChecked(zones.getInt(3) == 1);
                    zone5.setChecked(zones.getInt(4) == 1);
                    zone6.setChecked(zones.getInt(5) == 1);
                    zone7.setChecked(zones.getInt(6) == 1);
                    zone8.setChecked(zones.getInt(7) == 1);

                    tvTemperatures.setText("");
                    for (int i = 0; i < temps.length(); i++) {
                        tvTemperatures.append(Temperatures.from(i).get().getName() + ":\t\t" + temps.getDouble(i) + "C\n") ;
//                        tvTemperatures.append(val.toString() + "\n") ;
                    }

                    JSONArray pressures = json.getJSONArray("p");
                    tvPressures.setText("");
                    for (int i = 0; i < pressures.length(); i++) {
                        tvPressures.append(Pressures.from(i).get().getName() + ":\t\t" + pressures.getDouble(i) + "psi\n") ;

                    }

                } catch (Exception e) {
                    Log.e("Error", e.toString());
                }

            }

            @Override
            public void onCancelled(@NonNull DatabaseError error) {
                // calling on cancelled method when we receive
                // any error or we are not able to get the data.
                Toast.makeText(MainActivity.this, "Fail to get data.", Toast.LENGTH_SHORT).show();
            }
        });
    }

    private void signIn() {
        // [START sign_in_with_email]
        mAuth.signInWithEmailAndPassword(USERNAME, PASSWORD)
                .addOnCompleteListener(this, new OnCompleteListener<AuthResult>() {
                    @Override
                    public void onComplete(@NonNull Task<AuthResult> task) {
                        if (task.isSuccessful()) {
                            // Sign in success, update UI with the signed-in user's information
                            FirebaseUser user = mAuth.getCurrentUser();
                            updateUI(user);
                        } else {
                            // If sign in fails, display a message to the user.
                            Toast.makeText(MainActivity.this, "Authentication failed.",
                                    Toast.LENGTH_SHORT).show();
                            updateUI(null);
                        }
                    }
                });
        // [END sign_in_with_email]
    }
    private void updateUI( FirebaseUser user) {
        if (user != null) {
            tvAccountEmail.setText(user.getEmail());
            tvSignedIn.setChecked(true);
        } else {
            tvAccountEmail.setText("");
            tvSignedIn.setChecked(false);
        }
    }
}